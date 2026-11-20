import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync, mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const DIR = mkdtempSync(join(tmpdir(), "cad-data-"));
process.env.CAD_DATA_DIR = DIR + "/";
const S = await import("../src/store.js");

const A = S.userScope("aaaaaaaa-0000-0000-0000-000000000001");
const B = S.userScope("bbbbbbbb-0000-0000-0000-000000000002");
const PNG = Buffer.from("not-really-a-png").toString("base64");

test("hội thoại của tài khoản này không thấy, không đọc, không xóa được từ tài khoản khác", () => {
  S.putConversation(A, "conv-aaaa-0001", { title: "của A", items: [{ type: "image", mimeType: "image/png", data: PNG }] });
  assert.deepEqual(S.listConversations(B), []);
  assert.equal(S.getConversation(B, "conv-aaaa-0001"), null);
  S.deleteConversation(B, "conv-aaaa-0001");                         // xóa id của người khác: không có tác dụng
  assert.equal(S.getConversation(A, "conv-aaaa-0001")?.title, "của A");
  assert.equal(S.listConversations(A).length, 1);
});

test("ảnh nằm trong kho của chủ, người khác không tải được dù biết tên file", () => {
  const url = (S.getConversation(A, "conv-aaaa-0001")!.items as any[])[0].url as string;
  const name = url.split("/").pop()!;
  assert.ok(S.validFile(name));
  assert.ok(S.readImage(A, name));
  assert.equal(S.readImage(B, name), null);
});

test("cùng id hội thoại ở hai tài khoản là hai hội thoại riêng", () => {
  S.putConversation(B, "conv-aaaa-0001", { title: "của B" });
  assert.equal(S.getConversation(A, "conv-aaaa-0001")?.title, "của A");
  assert.equal(S.getConversation(B, "conv-aaaa-0001")?.title, "của B");
});

test("userScope chặn tên thư mục nguy hiểm", () => {
  for (const bad of ["../x", "a/b", "a\b", "", "A B", "x".repeat(65)]) assert.throws(() => S.userScope(bad));
});

test("phiên Claude CLI chỉ nối tiếp được khi do chính tài khoản đó tạo", () => {
  S.rememberCliSession(A, "sid-1");
  assert.equal(S.ownsCliSession(A, "sid-1"), true);
  assert.equal(S.ownsCliSession(B, "sid-1"), false);
  assert.equal(S.ownsCliSession(A, "sid-khac"), false);
});

test("dữ liệu cũ được giao cho một tài khoản, một lần, kèm phiên CLI cũ", () => {
  const lc = join(DIR, "conversations"), li = join(DIR, "images");
  mkdirSync(lc, { recursive: true }); mkdirSync(li, { recursive: true });
  writeFileSync(join(lc, "old-conv-0001.json"), JSON.stringify({ id: "old-conv-0001", title: "cũ", createdAt: 1, updatedAt: 2, engine: "cli", sessionId: "legacy-sid", history: [], items: [] }));
  writeFileSync(join(li, "0123456789abcdef0123456789abcdef.png"), "x");
  const C = S.userScope("cccccccc-0000-0000-0000-000000000003");
  assert.equal(S.adoptLegacy(C), 1);
  assert.equal(S.getConversation(C, "old-conv-0001")?.title, "cũ");
  assert.ok(S.readImage(C, "0123456789abcdef0123456789abcdef.png"));
  assert.equal(S.ownsCliSession(C, "legacy-sid"), true);
  assert.equal(existsSync(lc), false, "thư mục cũ đã được dọn");
  assert.equal(S.adoptLegacy(A), 0, "tài khoản sau không nhận lại được");
  assert.equal(S.getConversation(A, "old-conv-0001"), null);
});

test("xóa dữ liệu một tài khoản không đụng tới tài khoản khác", () => {
  S.putConversation(B, "conv-bbbb-0002", { title: "B giữ" });
  S.removeScopeData(A);
  assert.deepEqual(S.listConversations(A), []);
  assert.equal(S.getConversation(B, "conv-bbbb-0002")?.title, "B giữ");
});
