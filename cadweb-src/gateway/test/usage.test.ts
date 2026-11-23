import { test, after } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const USAGE_DIR = mkdtempSync(join(tmpdir(), "cad-usage-"));
process.env.CAD_DATA_DIR = USAGE_DIR + "/";
after(() => rmSync(USAGE_DIR, { recursive: true, force: true }));
const { usageOf, cleanUsage } = await import("../src/usage.js");
const S = await import("../src/store.js");

test("đọc usage từ kết quả của CLI/API, thiếu trường thì là 0", () => {
  // đúng dạng đã thấy ở `result.usage` của Claude CLI
  const u = usageOf({ input_tokens: 2, cache_creation_input_tokens: 3165, cache_read_input_tokens: 649, output_tokens: 4 }, 0.00076899);
  assert.deepEqual(u, { input: 2, output: 4, cacheRead: 649, cacheWrite: 3165, costUsd: 0.00076899 });
  assert.deepEqual(usageOf({ input_tokens: 5, output_tokens: 1 }), { input: 5, output: 1, cacheRead: 0, cacheWrite: 0 });
  assert.deepEqual(usageOf(undefined), { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 });
});

test("giá trị lạ (âm, chữ, NaN) không lọt vào dữ liệu lưu", () => {
  assert.deepEqual(cleanUsage({ input: -5, output: "x", cacheRead: NaN, cacheWrite: Infinity, costUsd: -1 }), { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 });
  assert.equal(cleanUsage("không phải object"), undefined);
  assert.equal(cleanUsage(null), undefined);
});

test("hội thoại lưu và đọc lại được usage; lưu lần sau không gửi usage thì giữ nguyên", () => {
  const sc = S.userScope("dddddddd-0000-0000-0000-000000000004");
  S.putConversation(sc, "conv-usage-01", { title: "t", usage: { input: 100, output: 20, cacheRead: 5, cacheWrite: 1, costUsd: 0.01 } });
  assert.deepEqual(S.getConversation(sc, "conv-usage-01")!.usage, { input: 100, output: 20, cacheRead: 5, cacheWrite: 1, costUsd: 0.01 });
  S.putConversation(sc, "conv-usage-01", { title: "đổi tên" });
  assert.equal(S.getConversation(sc, "conv-usage-01")!.usage!.input, 100);
});
