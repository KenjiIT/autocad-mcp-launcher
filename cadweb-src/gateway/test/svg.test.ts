// Hình agent vẽ trong chat (web/src/svg.ts): làm sạch SVG và tìm đường dẫn ảnh trong thư mục dự án.
import { test } from "node:test";
import assert from "node:assert/strict";
import { SVG_MAX, imageRefs, sanitizeSvg, svgDataUrl } from "../../web/src/svg.ts";

const OK = '<svg viewBox="0 0 10 10" xmlns="http://www.w3.org/2000/svg"><rect x="1" y="1" width="8" height="8" fill="url(#g)"/><text x="2" y="5">PK 20 m²</text></svg>';

test("SVG hợp lệ giữ nguyên nội dung vẽ (kể cả url(#id) nội bộ)", () => {
  const s = sanitizeSvg(OK)!;
  assert.ok(s.includes("<rect") && s.includes("PK 20 m²") && s.includes("url(#g)"));
  assert.ok(svgDataUrl(s).startsWith("data:image/svg+xml;charset=utf-8,%3Csvg"));
});

test("bỏ script, on*, foreignObject, liên kết ngoài, javascript:", () => {
  const bad = `<?xml version="1.0"?><!-- c --><svg viewBox="0 0 10 10" onload="alert(1)">
    <script>alert(1)</script><script src="http://x/y.js"/>
    <foreignObject><div onclick="x()">hi</div></foreignObject>
    <a href="https://evil.example"><text>link</text></a>
    <use xlink:href="#ok"/><image href="http://evil/i.png"/>
    <rect style="fill:url(http://evil/a.png)" ONMOUSEOVER='x()'/>
    <a href="javascript:alert(1)">j</a>
  </svg>`;
  const s = sanitizeSvg(bad)!;
  for (const x of ["<script", "alert(1)", "onload", "onclick", "ONMOUSEOVER", "foreignObject", "evil", "javascript:"]) assert.ok(!s.includes(x), x);
  assert.ok(s.includes('xlink:href="#ok"'), "liên kết nội bộ #id giữ lại");
  assert.ok(s.includes('xmlns="http://www.w3.org/2000/svg"'), "tự thêm xmlns để hiện được trong <img>");
});

test("không phải SVG hoặc quá lớn thì không hiện", () => {
  assert.equal(sanitizeSvg("<div>x</div>"), null);
  assert.equal(sanitizeSvg("<svg><rect/>"), null, "thiếu thẻ đóng");
  assert.equal(sanitizeSvg(""), null);
  assert.equal(sanitizeSvg(`<svg>${"x".repeat(SVG_MAX)}</svg>`), null);
});

test("đường dẫn ảnh agent nhắc: tuyệt đối trong dự án, tương đối, trong `...` có dấu cách; bỏ URL và ngoài dự án", () => {
  const dir = "C:\\Users\\u\\CAD Studio\\projects\\vẽ nhà";
  const t = [
    "Đã lưu `C:\\Users\\u\\CAD Studio\\projects\\vẽ nhà\\phuong-an\\PA-A.svg` và phuong-an/PA-B.svg.",
    "Ảnh khác: `phuong-an/PA A tầng 2.png`, ./anh/x.jpg, https://site/a.png, C:/Windows/x.png, ../ngoai.svg",
  ].join("\n");
  const r = imageRefs(t, dir);
  assert.deepEqual(r, ["phuong-an/PA-A.svg", "phuong-an/PA A tầng 2.png", "phuong-an/PA-B.svg", "anh/x.jpg"]);
  assert.deepEqual(imageRefs(t, null), []);
});
