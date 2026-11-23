// Bảng "Trong phiên này" (web/src/SessionPanel.tsx): tệp đã nhắc tới không bị liệt kê trùng.
import { test } from "node:test";
import assert from "node:assert/strict";
import { collect, fileLabels, pathKey } from "../../web/src/SessionPanel.tsx";

const tool = (input: unknown, text = "") => ({ kind: "tool", name: "Read", input, content: text ? [{ type: "text", text }] : [] });

test("cùng một tệp viết \\ hay /, hoa hay thường: chỉ một dòng", () => {
  const a = "C:\\Users\\u\\mcp\\.claude\\skills\\thiet-ke-phong-nha\\SKILL.md";
  const r = collect([
    tool({ file_path: a }),
    tool({ file_path: a.replace(/\\/g, "/") }),
    tool({}, JSON.stringify({ path: a.toUpperCase().replace("SKILL.MD", "SKILL.md") })),
  ]);
  assert.equal(r.files.length, 1);
  assert.equal(pathKey("C:\\A\\\\b/c.md"), "c:/a/b/c.md");
});

test("trùng tên khác đường dẫn: hiện thêm thư mục cha; tên không trùng giữ nguyên", () => {
  const paths = ["C:/s/thiet-ke-phong-nha/SKILL.md", "C:/s/mat-bang-tong-the/SKILL.md", "C:/s/thiet-ke-phong-nha/references/checklist.md"];
  assert.deepEqual(fileLabels(paths), ["thiet-ke-phong-nha/SKILL.md", "mat-bang-tong-the/SKILL.md", "checklist.md"]);
});
