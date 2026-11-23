import { test } from "node:test";
import assert from "node:assert/strict";
import { PICK_SRC, pickArgs } from "../src/pick.js";

const un = (s: string) => Buffer.from(s, "base64").toString("utf8");

test("tham số hộp chọn kiểu mới: base64 UTF-8 giữ nguyên dấu tiếng Việt, dấu cách và nháy", () => {
  const a = pickArgs("folder", "Mở dự án có sẵn: chọn thư mục", "D:\\Dự án\\Tòa 'A'");
  assert.equal(a[0], "folder");
  assert.equal(un(a[1]), "Mở dự án có sẵn: chọn thư mục");
  assert.equal(un(a[2]), "D:\\Dự án\\Tòa 'A'");
  assert.equal(a[3], "");
  assert.ok(a.every(x => /^[A-Za-z0-9+/=]*$/.test(x) || x === "folder"), "không có ký tự cần thoát trên dòng lệnh");
});

test("chọn file: bộ lọc gửi dạng 'Tên|mẫu' mỗi dòng; không có thư mục mở sẵn thì để trống", () => {
  const a = pickArgs("files", "Chọn file", undefined, [["Bản vẽ", "*.dwg;*.dxf"], ["Mọi file", "*.*"]]);
  assert.equal(a[0], "files"); assert.equal(a[2], "");
  assert.equal(un(a[3]), "Bản vẽ|*.dwg;*.dxf\nMọi file|*.*");
});

test("mã C# dùng IFileOpenDialog kiểu mới (FOS_PICKFOLDERS), không dùng FolderBrowserDialog", () => {
  assert.match(PICK_SRC, /DC1C5A9C-E88A-4dde-A5A1-60F82A20AEF7/);   // CLSID FileOpenDialog
  assert.match(PICK_SRC, /0x20u/);                                    // FOS_PICKFOLDERS
  assert.doesNotMatch(PICK_SRC, /FolderBrowserDialog/);
  assert.match(PICK_SRC, /Split\('\\n'\)/, "\\n trong mã C# phải là ký tự thoát, không phải xuống dòng thật");
});
