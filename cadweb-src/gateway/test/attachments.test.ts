import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync, readFileSync, statSync } from "node:fs";
import { AttachmentError, MAX_IMAGES, rebuildContent, splitContent, stage } from "../src/attachments.js";
import { codexArgs } from "../src/codex.js";
import { DEFAULT_CODEX_MODEL } from "../src/codexmodels.js";

// PNG 1x1 hợp lệ
const PNG = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==";
const img = (media_type = "image/png", data = PNG) => ({ type: "image", source: { type: "base64", media_type, data } });

test("chuỗi thường: không có ảnh", () => {
  assert.deepEqual(splitContent("xin chào"), { text: "xin chào", images: [] });
});

test("ảnh hợp lệ được tách khỏi chữ; dựng lại: ảnh trước, chữ sau", () => {
  const r = splitContent([img(), { type: "text", text: "mô tả giúp" }]);
  assert.equal(r.text, "mô tả giúp");
  assert.equal(r.images.length, 1);
  const out = rebuildContent(r.text, r.images) as any[];
  assert.equal(out[0].type, "image");
  assert.equal(out[1].text, "mô tả giúp");
});

test("chỉ ảnh, không chữ: có lời nhắc mặc định khi dựng lại", () => {
  const r = splitContent([img()]);
  const out = rebuildContent(r.text, r.images) as any[];
  assert.match(out[1].text, /ảnh/);
});

test("từ chối: loại lạ, SVG, base64 sai, sai chữ ký file, quá lớn, quá nhiều ảnh", () => {
  assert.throws(() => splitContent([img("image/svg+xml")]), AttachmentError);
  assert.throws(() => splitContent([img("application/pdf")]), AttachmentError);
  assert.throws(() => splitContent([img("image/png", "không phải base64!")]), AttachmentError);
  assert.throws(() => splitContent([img("image/jpeg", PNG)]), AttachmentError);               // PNG khai là JPEG
  assert.throws(() => splitContent([img("image/png", Buffer.from("MZ này là exe").toString("base64"))]), AttachmentError);
  assert.throws(() => splitContent([img("image/png", PNG.slice(0, 20) + "A".repeat(7_000_001))]), AttachmentError);
  assert.throws(() => splitContent(Array.from({ length: MAX_IMAGES + 1 }, () => img())), AttachmentError);
  assert.throws(() => splitContent([{ type: "image", source: { type: "url", url: "http://x/y.png" } }]), AttachmentError);
});

test("file tạm: ghi đúng nội dung, nằm trong thư mục riêng, xóa sạch khi xong", () => {
  const st = stage(splitContent([img(), img()]).images)!;
  assert.equal(st.files.length, 2);
  assert.ok(st.files.every(f => f.startsWith(st.dir) && f.endsWith(".png")));
  assert.deepEqual(readFileSync(st.files[0]), Buffer.from(PNG, "base64"));
  if (process.platform !== "win32") assert.equal(statSync(st.files[0]).mode & 0o077, 0);   // chỉ chủ đọc được
  st.cleanup();
  assert.equal(existsSync(st.dir), false);
  assert.equal(stage([]), undefined);
});

test("Codex: ảnh vào dòng lệnh dạng --image=<file>, đứng trước dấu '-' (stdin)", () => {
  const { args } = codexArgs({ model: DEFAULT_CODEX_MODEL, servers: [], allowed: [], images: ["C:\\t\\anh-1.png", "C:\\t\\anh-2.png"] });
  assert.ok(args.includes("--image=C:\\t\\anh-1.png") && args.includes("--image=C:\\t\\anh-2.png"));
  assert.equal(args[args.length - 1], "-");
  assert.ok(args.indexOf("--image=C:\\t\\anh-2.png") < args.length - 1);
  assert.ok(!codexArgs({ model: DEFAULT_CODEX_MODEL, servers: [], allowed: [] }).args.some(a => a.startsWith("--image")));
});
