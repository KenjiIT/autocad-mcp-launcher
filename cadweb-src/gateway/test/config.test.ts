import { test, after } from "node:test";
import assert from "node:assert/strict";

import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

// Dùng file cấu hình riêng (chưa tồn tại): kết quả không được phụ thuộc vào lựa chọn engine/model trong .config.json thật của người dùng
const CFG_DIR = mkdtempSync(join(tmpdir(), "cad-cfg-"));
process.env.CAD_CONFIG_FILE = join(CFG_DIR, "config.json");
after(() => rmSync(CFG_DIR, { recursive: true, force: true }));
delete process.env.CHAT_ENGINE;
const C = await import("../src/config.js");

test("chỉ nhận model trong danh sách cho phép, còn lại dùng mặc định", () => {
  const def = C.getModel();
  assert.equal(C.modelFor("claude-opus-5-5"), "claude-opus-5-5");
  assert.equal(C.modelFor("claude-haiku-5-5"), "claude-haiku-5-5");
  assert.equal(C.modelFor("model-la-tu-trinh-duyet"), def);
  assert.equal(C.modelFor(undefined), def);
  assert.equal(C.modelFor({ x: 1 }), def);
  assert.equal(C.modelFor("--dangerously-skip-permissions"), def, "không thể chèn tham số dòng lệnh qua tên model");
});

test("CHAT_MODELS đổi danh sách, model mặc định của admin luôn có trong danh sách", () => {
  process.env.CHAT_MODELS = "m-one:Một, m-two:Hai, bad id:Sai tên, ../x:Sai";
  const ids = C.getModels().map(m => m.id);
  assert.ok(ids.includes("m-one") && ids.includes("m-two"));
  assert.ok(!ids.includes("bad id") && !ids.includes("../x"));
  assert.ok(ids.includes(C.getModel()));
  assert.equal(C.modelFor("m-two"), "m-two");
  assert.equal(C.modelFor("claude-opus-5-5"), C.getModel(), "đã bị loại khỏi danh sách thì không dùng được");
  delete process.env.CHAT_MODELS;
});

test("engine codex: danh sách model và model mặc định là của Codex, không phải của Claude", async () => {
  process.env.CHAT_ENGINE = "codex";
  try {
    assert.equal(C.getEngine(), "codex");
    assert.equal(C.getModel(), "codex-default");
    assert.equal(C.getModels()[0].id, "codex-default");
    assert.ok(!C.getModels().some(m => m.id.startsWith("claude-")));
    assert.equal(C.modelFor("claude-opus-5-5"), "codex-default", "model của Claude không dùng được khi chạy Codex");
    assert.equal(C.modelFor("codex-default"), "codex-default");
  } finally { delete process.env.CHAT_ENGINE; }
});

test("engine theo từng phiên: model hợp lệ tính theo engine của phiên, không theo Cài đặt", () => {
  assert.equal(C.engineFor("codex"), "codex");
  assert.equal(C.engineFor("api"), "api");
  assert.equal(C.engineFor("rm -rf"), C.getEngine(), "engine lạ quay về mặc định");
  assert.equal(C.modelFor("claude-opus-5-5", "codex"), "codex-default");
  assert.equal(C.modelFor("claude-opus-5-5", "cli"), "claude-opus-5-5");
  assert.equal(C.getModel("codex"), "codex-default");
});
