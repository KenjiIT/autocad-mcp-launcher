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

function bucket(files) {
  return {
    get: async (key) => {
      const text = files[key];
      if (text === undefined) return null;
      return { body: text, size: new TextEncoder().encode(text).length };
    },
  };
}

function get(path, key = "khoa-nhom") {
  return new Request(`https://gw.test${path}`, { method: "GET", headers: { "x-team-key": key } });
}

test("dutoan: sai khóa thì 401, không đọc kho", async () => {
  const e = env({ DATA: bucket({ "manifest.json": "{}" }) });
  assert.equal((await worker.fetch(get("/dutoan/manifest", "sai"), e)).status, 401);
  assert.equal((await worker.fetch(get("/dutoan/db", ""), e)).status, 401);
});

test("dutoan: chưa gắn kho thì 503, chưa tải lên thì 404", async () => {
  assert.equal((await worker.fetch(get("/dutoan/manifest"), env())).status, 503);
  assert.equal((await worker.fetch(get("/dutoan/manifest"), env({ DATA: bucket({}) }))).status, 404);
});

test("dutoan: trả manifest và tệp, không cho cache", async () => {
  const e = env({ DATA: bucket({ "manifest.json": '{"sha256":"ab"}', "dutoan.db": "DULIEU" }) });
  const manifest = await worker.fetch(get("/dutoan/manifest"), e);
  assert.equal(manifest.status, 200);
  assert.match(manifest.headers.get("content-type"), /json/);
  assert.equal(await manifest.text(), '{"sha256":"ab"}');
  const db = await worker.fetch(get("/dutoan/db"), e);
  assert.equal(db.status, 200);
  assert.equal(db.headers.get("content-length"), "6");
  assert.equal(db.headers.get("cache-control"), "private, no-store");
  assert.equal(await db.text(), "DULIEU");
});

test("dutoan: POST không được phép", async () => {
  const r = await worker.fetch(new Request("https://gw.test/dutoan/db", { method: "POST", headers: { "x-team-key": "khoa-nhom" } }), env({ DATA: bucket({}) }));
  assert.equal(r.status, 404);
});

test("dutoan: có DUTOAN_KEY thì khóa nhóm chung không mở được", async () => {
  const e = env({ DUTOAN_KEY: "khoa-du-toan", DATA: bucket({ "manifest.json": "{}" }) });
  assert.equal((await worker.fetch(get("/dutoan/manifest", "khoa-nhom"), e)).status, 401);
  assert.equal((await worker.fetch(get("/dutoan/manifest", "khoa-du-toan"), e)).status, 200);
});
