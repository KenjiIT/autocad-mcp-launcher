// Xóa dự án kèm thư mục: chỉ xóa đúng thư mục của dự án, từ chối các thư mục quan trọng; báo file đang bị khoá.
import { test, after } from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const TMP = mkdtempSync(join(tmpdir(), "cad-del-"));
process.env.CAD_DATA_DIR = join(TMP, "data") + "/";
process.env.CAD_PROJECTS_DIR = join(TMP, "CAD Studio", "projects");
after(() => rmSync(TMP, { recursive: true, force: true }));

const P = await import("../src/projects.js");
const proj = (id: string, dir: string | null) => ({ id, name: id, dir, createdAt: 1 });
const HOME = join(TMP, "home");
const PROTECTED = [HOME, join(HOME, "Desktop"), join(HOME, "Documents"), join(HOME, "Downloads"), process.env.CAD_PROJECTS_DIR!, join(TMP, "CAD Studio")];

test("thư mục dự án bình thường thì được xóa", () => {
  const a = proj("a", join(TMP, "CAD Studio", "projects", "vẽ nhà"));
  assert.equal(P.deleteFolderProblem(a, [a, proj("b", join(TMP, "khac"))], PROTECTED), null);
});

test("từ chối ổ gốc, home, Desktop/Documents/Downloads, thư mục projects và thư mục cha của nó", () => {
  for (const d of ["C:\\", "D:\\", ...PROTECTED, join(HOME, "Documents") + "\\"]) {
    const p = proj("x", d);
    assert.ok(P.deleteFolderProblem(p, [p], PROTECTED), d);
  }
  const parentOfHome = proj("y", TMP);   // chứa cả home và CAD Studio
  assert.match(P.deleteFolderProblem(parentOfHome, [parentOfHome], PROTECTED)!, /chứa/);
});

test("từ chối khi chứa, nằm trong, hoặc trùng thư mục dự án khác; không có thư mục thì báo", () => {
  const outer = proj("outer", join(TMP, "du-an"));
  const inner = proj("inner", join(TMP, "du-an", "con"));
  const twin = proj("twin", join(TMP, "du-an") + "\\");
  assert.match(P.deleteFolderProblem(outer, [outer, inner], PROTECTED)!, /chứa thư mục của dự án "inner"/);
  assert.match(P.deleteFolderProblem(inner, [outer, inner], PROTECTED)!, /nằm trong thư mục của dự án "outer"/);
  assert.match(P.deleteFolderProblem(outer, [outer, twin], PROTECTED)!, /cũng là của dự án "twin"/);
  assert.ok(P.deleteFolderProblem(proj("n", null), [], PROTECTED));
  // tên gần giống (du-an-2) không bị coi là nằm trong du-an
  const sib = proj("sib", join(TMP, "du-an-2"));
  assert.equal(P.deleteFolderProblem(sib, [outer, sib], PROTECTED), null);
});

test("đếm file và dung lượng thư mục", () => {
  const d = join(TMP, "dem"); mkdirSync(join(d, "a"), { recursive: true });
  writeFileSync(join(d, "x.txt"), "12345"); writeFileSync(join(d, "a", "y.txt"), "123");
  assert.deepEqual(P.folderStats(d), { files: 2, bytes: 8, capped: false });
  assert.equal(P.folderStats(d, 1).capped, true);
  assert.deepEqual(P.folderStats(join(TMP, "khong-co")), { files: 0, bytes: 0, capped: false });
});

test("báo đúng file đang bị chương trình khác giữ", { skip: process.platform !== "win32" }, async () => {
  const d = join(TMP, "khoa"); mkdirSync(d, { recursive: true });
  const f = join(d, "ban-ve.dwg"); writeFileSync(f, "x"); writeFileSync(join(d, "tu-do.txt"), "y");
  // Một tiến trình khác mở file với FileShare.None (giống AutoCAD giữ bản vẽ đang mở)
  const holder = spawn("powershell.exe", ["-NoProfile", "-Command",
    `$h=[IO.File]::Open('${f.replace(/'/g, "''")}','Open','ReadWrite','None'); 'ok'; Start-Sleep 20`], { stdio: ["ignore", "pipe", "ignore"] });
  await new Promise<void>(res => holder.stdout.once("data", () => res()));
  try {
    assert.deepEqual(P.lockedFiles(d), [f]);
  } finally { holder.kill(); await new Promise(r => holder.once("exit", r)); }
  assert.deepEqual(P.lockedFiles(d), []);
});
