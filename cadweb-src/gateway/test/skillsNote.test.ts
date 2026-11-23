import { test } from "node:test";
import assert from "node:assert/strict";
import { skillsNote } from "../src/skillsNote.js";
import { codexArgs } from "../src/codex.js";

const L = [{ name: "thiet-ke-phong-nha", description: "Thiết kế nhà ở: hỏi nhu cầu, đưa phương án, kiểm tra." }, { name: "mat-bang-tong-the", description: "x ".repeat(200) }];

test("khối skill: lời dặn nạp skill trước khi làm, liệt kê tên + mô tả đã cắt", () => {
  const n = skillsNote(L);
  assert.match(n, /TRƯỚC KHI LÀM/);
  assert.match(n, /operation=get, name=<tên>/);
  assert.match(n, /Không bỏ bước/);
  assert.match(n, /- thiet-ke-phong-nha: Thiết kế nhà ở/);
  const line = n.split("\n").find(l => l.startsWith("- mat-bang-tong-the"))!;
  assert.ok(line.length < 140 && line.endsWith("…"), "mô tả dài bị cắt");
  assert.equal(skillsNote([]), "", "không có skill thì không chèn gì");
});

test("khối skill giữ gọn: nhiều skill thì dừng ở giới hạn và báo còn lại", () => {
  const many = Array.from({ length: 200 }, (_, i) => ({ name: `skill-${i}`, description: "mô tả ".repeat(30) }));
  const n = skillsNote(many);
  assert.ok(n.length <= 3700, String(n.length));
  assert.match(n, /… và \d+ skill khác/);
});

test("Codex: khối skill nằm trong developer_instructions", () => {
  const { args } = codexArgs({ model: "m", servers: [], allowed: [], extra: skillsNote(L) });
  const di = args[args.findIndex(a => a.startsWith("developer_instructions=")) ];
  assert.ok(di && di.includes("thiet-ke-phong-nha") && di.includes("TRƯỚC KHI LÀM"));
});
