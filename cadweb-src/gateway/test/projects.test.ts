import { test, after } from "node:test";
import assert from "node:assert/strict";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

// Dữ liệu app và thư mục dự án đều nằm trong một thư mục tạm, xóa khi xong.
const TMP = mkdtempSync(join(tmpdir(), "cad-proj-"));
const DATA = join(TMP, "data"), PROJ = join(TMP, "projects");
process.env.CAD_DATA_DIR = DATA + "/";
process.env.CAD_PROJECTS_DIR = PROJ;
after(() => rmSync(TMP, { recursive: true, force: true }));

// Dữ liệu kiểu cũ: dự án "a" có thư mục, chat của nó ở data/projects/<id>; một thư mục mồ côi; chat "Chung" cũ ở data/users/local.
const dirA = join(TMP, "Toa A"); mkdirSync(join(dirA, ".git"), { recursive: true });
mkdirSync(DATA, { recursive: true });
writeFileSync(join(DATA, "projects.json"), JSON.stringify([
  { id: "aaaaaaaaaaaa", name: "Tòa A", dir: dirA, createdAt: 1 },
]));
const conv = (id: string, title: string) => JSON.stringify({ id, title, createdAt: 1, updatedAt: 2, engine: "cli", history: [], items: [] });
const legacy = (rel: string, id: string, title: string, img?: string) => {
  mkdirSync(join(DATA, rel, "conversations"), { recursive: true });
  writeFileSync(join(DATA, rel, "conversations", id + ".json"), conv(id, title));
  if (img) { mkdirSync(join(DATA, rel, "images"), { recursive: true }); writeFileSync(join(DATA, rel, "images", img), "png"); }
};
const IMG = "0123456789abcdef0123456789abcdef.png";
legacy("projects/aaaaaaaaaaaa", "conv-a-000001", "chat A", IMG);
legacy("projects/bbbbbbbbbbbb", "conv-b-000001", "mồ côi");
legacy("users/local", "conv-u-000001", "chat Chung");

const P = await import("../src/projects.js");
const S = await import("../src/store.js");

test("migration: chat cũ chuyển vào .cadstudio của dự án, chat không rõ dự án vào dự án mặc định, thư mục cũ dọn sau khi chép", () => {
  const [a] = P.listProjects();
  const sc = P.scopeOf(a.id)!;
  const titles = S.listConversations(sc).map(c => c.title).sort();
  assert.deepEqual(titles, ["chat A", "chat Chung", "mồ côi"]);
  assert.ok(existsSync(join(dirA, ".cadstudio", "conversations", "conv-a-000001.json")));
  assert.ok(S.readImage(sc, IMG), "ảnh đi theo dự án");
  assert.equal(existsSync(join(DATA, "projects", "aaaaaaaaaaaa")), false);
  assert.equal(existsSync(join(DATA, "users", "local")), false);
});

test("repo git: .cadstudio/ được thêm vào .gitignore đúng một lần", () => {
  const gi = readFileSync(join(dirA, ".gitignore"), "utf8");
  assert.equal(gi.match(/^\.cadstudio\/$/gm)?.length, 1);
  S.ignoreInGit(dirA);
  assert.equal(readFileSync(join(dirA, ".gitignore"), "utf8"), gi);
});

test("cài lại app (mất thư mục data): mở lại thư mục dự án là thấy chat và ảnh", () => {
  rmSync(DATA, { recursive: true, force: true });
  const r = P.createProject("Tòa A mở lại", dirA);
  assert.ok("project" in r);
  const sc = P.scopeOf(r.project.id)!;
  assert.equal(S.listConversations(sc).length, 3, "không thêm phiên trống khi đã có chat");
  assert.ok(S.readImage(sc, IMG));
});

test("dự án mới không có .cadstudio: tạo phiên trống trong thư mục dự án; dự án khác không thấy", () => {
  const dirB = join(TMP, "Toa B"); mkdirSync(dirB);
  const r = P.createProject("Tòa B", dirB);
  assert.ok("project" in r);
  const sb = P.scopeOf(r.project.id)!;
  assert.equal(S.listConversations(sb).length, 1);
  assert.equal(existsSync(join(dirB, ".gitignore")), false, "không phải repo git: không tạo .gitignore");
  assert.equal(S.readImage(sb, IMG), null);
  assert.ok(!P.listFiles(r.project, "")!.some(e => e.name === ".cadstudio"), ".cadstudio ẩn khỏi cây file");
});

test(".cadstudio là junction trỏ ra ngoài dự án thì bị từ chối", () => {
  const dirC = join(TMP, "Toa C"), outside = join(TMP, "ngoai");
  mkdirSync(dirC); mkdirSync(outside);
  symlinkSync(outside, join(dirC, ".cadstudio"), "junction");
  assert.throws(() => S.listConversations({ kind: "project", id: "cccccccccccc", dir: dirC }));
});

test("mở dự án có sẵn: đếm phiên trong .cadstudio, đặt tên theo thư mục, mở lại không tạo trùng", () => {
  const dir = join(TMP, "Cu"); mkdirSync(join(dir, ".cadstudio", "conversations"), { recursive: true });
  writeFileSync(join(dir, ".cadstudio", "conversations", "c1.json"), conv("c1", "cũ 1"));
  writeFileSync(join(dir, ".cadstudio", "conversations", "c2.json"), conv("c2", "cũ 2"));
  const r = P.openProject(dir);
  assert.ok(!("error" in r));
  assert.equal(r.existed, false); assert.equal(r.sessions, 2); assert.equal(r.project.name, "Cu");
  const n = P.listProjects().length;
  const again = P.openProject(dir + "/");
  assert.ok(!("error" in again));
  assert.equal(again.existed, true); assert.equal(again.project.id, r.project.id); assert.equal(again.sessions, 2);
  assert.equal(P.listProjects().length, n, "không thêm dự án trùng");
});

test("mở dự án: trùng tên thì thêm số; đường dẫn sai hoặc không tồn tại thì báo lỗi, không tạo gì", () => {
  const other = join(TMP, "x", "Cu"); mkdirSync(other, { recursive: true });
  const r = P.openProject(other);
  assert.ok(!("error" in r)); assert.equal(r.project.name, "Cu (2)"); assert.equal(r.sessions, 0);
  assert.ok("error" in P.openProject("relative/path"));
  assert.ok("error" in P.openProject(join(TMP, "khong-co")));
  assert.ok(!existsSync(join(TMP, "khong-co")));
});

test("tìm thư mục kéo thả theo tên trong các thư mục gốc (sâu 2 cấp), bỏ tên chứa dấu gạch", () => {
  const root = join(TMP, "roots"); mkdirSync(join(root, "a", "Keo Tha"), { recursive: true }); mkdirSync(join(root, "Keo Tha"), { recursive: true });
  assert.deepEqual(P.locateFolder("keo tha", [root]).sort(), [join(root, "Keo Tha"), join(root, "a", "Keo Tha")].sort());
  assert.deepEqual(P.locateFolder("../etc", [root]), []);
  assert.deepEqual(P.locateFolder("", [root]), []);
});
