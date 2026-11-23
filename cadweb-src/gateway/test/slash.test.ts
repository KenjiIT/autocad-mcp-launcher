// Menu "/" của ô soạn tin (web/src/slash.ts): mở ở bất kỳ đâu sau khoảng trắng, chèn đúng chỗ, nhận skill giữa câu.
import { test } from "node:test";
import assert from "node:assert/strict";
import { insertSkill, mentionedSkills, skillPrompt, slashAt, splitSkills } from "../../web/src/slash.ts";

const K = ["thiet-ke-phong-nha", "mat-bang-tong-the"];

test("mở menu khi '/' ở đầu ô hoặc ngay sau khoảng trắng/xuống dòng, kể cả giữa câu", () => {
  assert.deepEqual(slashAt("/", 1), { start: 0, query: "" });
  assert.deepEqual(slashAt("/thiet", 6), { start: 0, query: "thiet" });
  const t = "phương án nhà này xấu quá bạn không dùng /";
  assert.deepEqual(slashAt(t, t.length), { start: t.length - 1, query: "" });
  assert.deepEqual(slashAt("dòng 1\n/mat", 11), { start: 7, query: "mat" });
  assert.deepEqual(slashAt("a /thi rồi b", 6), { start: 2, query: "thi" }, "con trỏ ở giữa câu");
});

test("không mở khi '/' nằm trong đường dẫn hay URL, hoặc con trỏ đã qua dấu cách", () => {
  for (const s of ["C:/", "mở C:/Du an", "http://", "xem https://a.b/c", "a/b", "1/2"]) assert.equal(slashAt(s, s.length), null, s);
  assert.equal(slashAt("/thiet ", 7), null);
});

test("chèn skill đúng chỗ con trỏ, giữ nguyên chữ trước và sau", () => {
  const t = "bạn không dùng /thi cho nhà này";
  const r = insertSkill(t, "bạn không dùng /thi".length, "thiet-ke-phong-nha");
  assert.equal(r.text, "bạn không dùng /thiet-ke-phong-nha cho nhà này");
  assert.equal(r.text.slice(0, r.caret), "bạn không dùng /thiet-ke-phong-nha ");
  const end = insertSkill("xấu quá /", 9, "mat-bang-tong-the");
  assert.equal(end.text, "xấu quá /mat-bang-tong-the ");
  assert.equal(end.caret, end.text.length);
  const mid = insertSkill("a /thXX b", 5, "thiet-ke-phong-nha");   // con trỏ giữa từ: thay cả từ
  assert.equal(mid.text, "a /thiet-ke-phong-nha b");
  assert.deepEqual(insertSkill("C:/x", 3, "thiet-ke-phong-nha"), { text: "C:/x", caret: 3 });
});

test("skill nhắc giữa câu vẫn được nhận diện và dặn nạp như khi đặt ở đầu", () => {
  const t = "phương án nhà này xấu quá bạn không dùng /thiet-ke-phong-nha à, xem C:/x và /khong-co";
  assert.deepEqual(mentionedSkills(t, K), ["thiet-ke-phong-nha"]);
  const p = skillPrompt(t, K);
  assert.match(p, /^Hãy dùng skill "thiet-ke-phong-nha" \(nạp bằng tool skills, operation=get, name=thiet-ke-phong-nha\)/);
  assert.ok(p.endsWith(t), "giữ nguyên câu khi skill ở giữa");
  const lead = skillPrompt("/thiet-ke-phong-nha vẽ nhà 2 tầng", K);
  assert.ok(lead.endsWith("\n\nvẽ nhà 2 tầng"), "skill ở đầu: bỏ /tên khỏi yêu cầu như trước");
  assert.match(skillPrompt("/mat-bang-tong-the rồi /thiet-ke-phong-nha", K), /skill "mat-bang-tong-the", "thiet-ke-phong-nha"/);
  assert.equal(skillPrompt("không có skill /abc", K), "không có skill /abc");
});

test("bong bóng tin: skill ở bất kỳ đâu thành chip", () => {
  assert.deepEqual(splitSkills("xấu quá /thiet-ke-phong-nha nhé", K), [{ text: "xấu quá " }, { skill: "thiet-ke-phong-nha" }, { text: " nhé" }]);
  assert.deepEqual(splitSkills("/mat-bang-tong-the", K), [{ skill: "mat-bang-tong-the" }]);
  assert.deepEqual(splitSkills("C:/thiet-ke-phong-nha", K), [{ text: "C:/thiet-ke-phong-nha" }]);
});
