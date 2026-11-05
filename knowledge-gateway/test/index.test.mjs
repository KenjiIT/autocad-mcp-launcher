import assert from "node:assert/strict";
import test from "node:test";
import worker from "../src/index.js";

const GOOD = `---
title: Thử
type: pitfall
topics: [cad]
status: draft
source: Phiên thử
updated: 2026-11-05
reviewed_by:
---
Nội dung hợp lệ.
`;

function env(extra = {}) {
  const store = new Map();
  return {
    TEAM_KEY: "khoa-nhom",
    GITHUB_TOKEN: "ghp_" + "x".repeat(30),
    INBOX_REPO: "owner/inbox",
    SENSITIVE_TERMS: "MADUANX,Tên Khách",
    RATE: { get: async (k) => store.get(k) ?? null, put: async (k, v) => void store.set(k, v) },
    ...extra,
  };
}

function post(body, key = "khoa-nhom") {
  return new Request("https://gw.test/propose", {
    method: "POST",
    headers: { "x-team-key": key },
    body: typeof body === "string" ? body : JSON.stringify(body),
  });
}

function mockGithub(status = 201) {
  const calls = [];
  globalThis.fetch = async (url, init) => {
    calls.push({ url, init });
    return new Response("{}", { status });
  };
  return calls;
}

test("health", async () => {
  const r = await worker.fetch(new Request("https://gw.test/health"), env());
  assert.equal(r.status, 200);
});

test("sai khóa nhóm bị từ chối và không gọi GitHub", async () => {
  const calls = mockGithub();
  const r = await worker.fetch(post({ slug: "a", content: GOOD }, "sai"), env());
  assert.equal(r.status, 401);
  assert.equal(calls.length, 0);
});

test("đề xuất hợp lệ được ghi vào inbox", async () => {
  const calls = mockGithub();
  const r = await worker.fetch(post({ slug: "loi-lt", content: GOOD, sender: "may-A" }), env());
  assert.equal(r.status, 201);
  const out = await r.json();
  assert.match(out.path, /^proposals\/\d{4}-\d{2}-\d{2}-loi-lt-[0-9a-f]{8}\.md$/);
  assert.equal(calls.length, 1);
  assert.match(calls[0].url, /repos\/owner\/inbox\/contents\/proposals\//);
  assert.equal(calls[0].init.headers.authorization.startsWith("Bearer ghp_"), true);
  const sent = JSON.parse(calls[0].init.body);
  assert.equal(Buffer.from(sent.content, "base64").toString("utf8"), GOOD);
});

test("slug sai", async () => {
  mockGithub();
  const r = await worker.fetch(post({ slug: "../x", content: GOOD }), env());
  assert.equal(r.status, 400);
});

test("body không phải JSON", async () => {
  mockGithub();
  assert.equal((await worker.fetch(post("không phải json"), env())).status, 400);
});

test("nội dung nhạy cảm bị chặn", async () => {
  const calls = mockGithub();
  for (const bad of ["Liên hệ a@b.com", "Lô MADUANX-3", "C:\\Users\\an\\x", "Gọi 0912345678"]) {
    const r = await worker.fetch(post({ slug: "a", content: GOOD + bad }), env());
    assert.equal(r.status, 422, bad);
  }
  assert.equal(calls.length, 0);
});

test("thiếu đầu trang, đã có reviewed_by, không phải draft", async () => {
  mockGithub();
  assert.equal((await worker.fetch(post({ slug: "a", content: "chỉ có chữ" }), env())).status, 422);
  const reviewed = GOOD.replace("reviewed_by:", "reviewed_by: ai-do");
  assert.equal((await worker.fetch(post({ slug: "a", content: reviewed }), env())).status, 422);
  const confirmed = GOOD.replace("status: draft", "status: confirmed");
  assert.equal((await worker.fetch(post({ slug: "a", content: confirmed }), env())).status, 422);
});

test("quá lớn", async () => {
  mockGithub();
  const r = await worker.fetch(post({ slug: "a", content: GOOD + "x".repeat(60000) }), env());
  assert.equal(r.status, 413);
});

test("giới hạn mỗi ngày", async () => {
  mockGithub();
  const e = env({ DAILY_LIMIT: "2" });
  assert.equal((await worker.fetch(post({ slug: "a", content: GOOD }), e)).status, 201);
  assert.equal((await worker.fetch(post({ slug: "b", content: GOOD }), e)).status, 201);
  assert.equal((await worker.fetch(post({ slug: "c", content: GOOD }), e)).status, 429);
});

test("GitHub lỗi thì báo 502", async () => {
  mockGithub(401);
  assert.equal((await worker.fetch(post({ slug: "a", content: GOOD }), env())).status, 502);
});
