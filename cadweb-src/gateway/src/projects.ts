import { randomBytes } from "node:crypto";
import { copyFileSync, cpSync, rmSync, existsSync, mkdirSync, readdirSync, readFileSync, renameSync, statSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { fileURLToPath } from "node:url";
import { basename, dirname, extname, isAbsolute, join, relative, resolve } from "node:path";
import { listConversations, putConversation, removeScopeData, type Scope } from "./store.js";

// Dự án kiểu Orca: mỗi dự án là MỘT THƯ MỤC trên máy. Hội thoại và ảnh của dự án lưu riêng (data/projects/<id>/),
// còn Claude CLI / Codex chạy với thư mục làm việc là thư mục dự án và được đọc/ghi file trong đó.
// Luôn có ít nhất một dự án: máy mới tự có dự án "master" kèm một phiên chat.
const DATA = process.env.CAD_DATA_DIR ?? fileURLToPath(new URL("../data/", import.meta.url));
const FILE = join(DATA, "projects.json");
export const PROJECTS_ROOT = process.env.CAD_PROJECTS_DIR ?? join(homedir(), "CAD Studio", "projects");
export const STARTER_TITLE = "Phiên chat mới";

export type Project = { id: string; name: string; dir: string | null; createdAt: number; pinned?: boolean; shell?: boolean };   // shell: cho agent chạy lệnh (Bash) trong thư mục dự án

const load = (): Project[] => { try { return JSON.parse(readFileSync(FILE, "utf8")); } catch { return []; } };
const save = (list: Project[]) => { mkdirSync(DATA, { recursive: true }); writeFileSync(FILE + ".tmp", JSON.stringify(list, null, 2)); renameSync(FILE + ".tmp", FILE); };
const scopeFor = (id: string): Scope => ({ kind: "project", id });

/** Một phiên chat trống để dự án mới có sẵn chỗ bắt đầu (hiện ngay trong cây dự án). */
const addStarter = (id: string) => putConversation(scopeFor(id), randomBytes(8).toString("hex"), { title: STARTER_TITLE, items: [], history: [] });

/** Máy mới: tạo dự án "master" + một phiên chat. Hội thoại của dự án "Chung" cũ (data/users/local) chuyển vào master. */
function ensureDefault(): Project[] {
  const list = load();
  const legacy = join(DATA, "users", "local");
  if (list.length && !existsSync(legacy)) return list;
  const dir = join(PROJECTS_ROOT, "master");
  mkdirSync(dir, { recursive: true });
  const master: Project = { id: randomBytes(6).toString("hex"), name: "master", dir, createdAt: Date.now() };
  if (existsSync(legacy)) {
    const to = join(DATA, "projects", master.id);
    mkdirSync(join(DATA, "projects"), { recursive: true });
    renameSync(legacy, to);
    // Phiên Claude CLI cũ chạy ở thư mục tạm, không nối tiếp được trong thư mục master: bỏ để bắt đầu phiên mới.
    rmSync(join(to, "cli-sessions.json"), { force: true });
  }
  const all = [master, ...list];
  save(all);
  if (!listConversations(scopeFor(master.id)).length) addStarter(master.id);
  return all;
}

/** Dự án ghim lên đầu, còn lại giữ thứ tự tạo. */
export const listProjects = (): Project[] => { const l = ensureDefault(); return [...l.filter(p => p.pinned), ...l.filter(p => !p.pinned)]; };
/** Không nêu dự án (hoặc nêu dự án đã xóa) thì null; route tự báo lỗi. Bỏ trống id thì là dự án đầu tiên. */
export const getProject = (id: string | undefined | null): Project | undefined => { const l = listProjects(); return id ? l.find(p => p.id === id) : l[0]; };

/** Phạm vi lưu hội thoại của một dự án; dự án không tồn tại thì null. */
export function scopeOf(id: string | undefined | null): Scope | null {
  const p = getProject(id);
  return p ? scopeFor(p.id) : null;
}

const safeFolder = (name: string) => name.replace(/[<>:"/\\|?*\x00-\x1f]/g, " ").replace(/\s+/g, " ").trim().replace(/[. ]+$/, "").slice(0, 80);

export function createProject(name: unknown, dir: unknown): { project: Project } | { error: string } {
  const n = typeof name === "string" ? name.trim().slice(0, 80) : "";
  if (!n) return { error: "Nhập tên dự án." };
  const list = listProjects();
  if (list.some(p => p.name.toLowerCase() === n.toLowerCase())) return { error: "Đã có dự án cùng tên." };
  let folder: string;
  if (typeof dir === "string" && dir.trim()) {
    folder = resolve(dir.trim());
    if (!isAbsolute(dir.trim())) return { error: "Thư mục phải là đường dẫn đầy đủ, ví dụ D:\\Du an\\Toa A." };
    if (!existsSync(folder) || !statSync(folder).isDirectory()) return { error: "Không thấy thư mục này trên máy." };
  } else {
    const f = safeFolder(n);
    if (!f) return { error: "Tên dự án không dùng làm tên thư mục được." };
    folder = join(PROJECTS_ROOT, f);
    mkdirSync(folder, { recursive: true });
  }
  if (list.some(p => p.dir && resolve(p.dir).toLowerCase() === folder.toLowerCase())) return { error: "Thư mục này đã thuộc một dự án khác." };
  const project: Project = { id: randomBytes(6).toString("hex"), name: n, dir: folder, createdAt: Date.now() };
  save([...list, project]);
  addStarter(project.id);
  return { project };
}

/** Đổi tên và/hoặc ghim/bỏ ghim (trường nào không gửi thì giữ nguyên). */
export function updateProject(id: string, b: { name?: unknown; pinned?: unknown; shell?: unknown }): { project: Project } | { error: string } {
  const list = load(), p = list.find(x => x.id === id);
  if (!p) return { error: "Không có dự án này." };
  if (b.name !== undefined) {
    const n = typeof b.name === "string" ? b.name.trim().slice(0, 80) : "";
    if (!n) return { error: "Nhập tên dự án." };
    if (list.some(x => x.id !== id && x.name.toLowerCase() === n.toLowerCase())) return { error: "Đã có dự án cùng tên." };
    p.name = n;
  }
  if (typeof b.pinned === "boolean") p.pinned = b.pinned || undefined;
  if (typeof b.shell === "boolean") p.shell = b.shell || undefined;
  save(list);
  return { project: p };
}

/** Bỏ dự án khỏi CAD Studio cùng hội thoại của nó. KHÔNG xóa thư mục dự án trên máy. */
export function deleteProject(id: string): boolean | "last" {
  const list = load();
  if (!list.some(p => p.id === id)) return false;
  if (list.length === 1) return "last";
  save(list.filter(p => p.id !== id));
  removeScopeData({ kind: "project", id });
  return true;
}

// ---- File trong thư mục dự án (cây file ở cột phải) ----
export type Entry = { name: string; path: string; dir: boolean; size: number; mtime: number };
const HIDDEN = new Set([".git", "node_modules", ".venv", "__pycache__"]);

/** Đường dẫn con nằm TRONG thư mục dự án; ra ngoài (../, ổ khác) thì null. */
export function inside(p: Project, sub: string): string | null {
  if (!p.dir) return null;
  const root = resolve(p.dir), full = resolve(root, sub || ".");
  const rel = relative(root, full);
  return rel === "" || (!rel.startsWith("..") && !isAbsolute(rel)) ? full : null;
}

export function listFiles(p: Project, sub: string): Entry[] | null {
  const d = inside(p, sub);
  if (!d || !existsSync(d) || !statSync(d).isDirectory()) return null;
  return readdirSync(d, { withFileTypes: true })
    .filter(e => !HIDDEN.has(e.name))
    .flatMap(e => {
      try {
        const st = statSync(join(d, e.name));
        return [{ name: e.name, path: relative(resolve(p.dir!), join(d, e.name)).replace(/\\/g, "/"), dir: st.isDirectory(), size: st.size, mtime: st.mtimeMs }];
      } catch { return []; }
    })
    .sort((a, b) => Number(b.dir) - Number(a.dir) || a.name.localeCompare(b.name, "vi"));
}

/** Chép file người dùng chọn vào thư mục dự án; trùng tên thì thêm " (2)", " (3)"… */
export function importFiles(p: Project, files: unknown): { copied: string[] } | { error: string } {
  if (!p.dir) return { error: "Dự án này không có thư mục." };
  if (!Array.isArray(files) || !files.every(f => typeof f === "string")) return { error: "Danh sách file không hợp lệ." };
  const copied: string[] = [];
  for (const src of files as string[]) {
    if (!isAbsolute(src) || !existsSync(src) || !statSync(src).isFile()) continue;
    const ext = extname(src), stem = basename(src, ext);
    let dest = join(p.dir, basename(src));
    for (let i = 2; existsSync(dest); i++) dest = join(p.dir, `${stem} (${i})${ext}`);
    copyFileSync(src, dest);
    copied.push(basename(dest));
  }
  return { copied };
}

// Ký tự Windows không cho dùng, và các tên thiết bị dành riêng (CON, NUL, COM1…) — tạo ra thì không xóa được bằng cách thường.
const BAD_NAME = /[<>:"/\\|?*\x00-\x1f]/;
const RESERVED = /^(con|prn|aux|nul|com\d|lpt\d)(\..*)?$/i;
const BAD_MSG = 'Tên không hợp lệ (không dùng < > : " / \\ | ? *, và không đặt CON, NUL, COM1…).';
const nameOk = (n: string) => !!n && !BAD_NAME.test(n) && !RESERVED.test(n) && n !== "." && n !== ".." && !/[. ]$/.test(n);
const relOf = (p: Project, full: string) => relative(resolve(p.dir!), full).replace(/\\/g, "/");

/** Đổi tên file/thư mục, giữ nguyên chỗ. */
export function renameEntry(p: Project, path: unknown, name: unknown): { path: string } | { error: string } {
  const n = typeof name === "string" ? name.trim() : "";
  if (!nameOk(n)) return { error: BAD_MSG };
  const full = typeof path === "string" && path ? inside(p, path) : null;
  if (!full || full === resolve(p.dir!) || !existsSync(full)) return { error: "Không có file/thư mục này trong dự án." };
  const to = join(dirname(full), n);
  if (existsSync(to) && to.toLowerCase() !== full.toLowerCase()) return { error: `Đã có "${n}" trong thư mục này.` };
  renameSync(full, to);
  return { path: relOf(p, to) };
}

/** Kéo thả trong cây: chuyển file/thư mục sang thư mục khác của dự án (không ghi đè). */
export function moveEntry(p: Project, src: unknown, parent: unknown): { path: string } | { error: string } {
  const from = typeof src === "string" && src ? inside(p, src) : null;
  const dir = inside(p, typeof parent === "string" ? parent : "");
  if (!from || from === resolve(p.dir!) || !existsSync(from)) return { error: "Không có file/thư mục này trong dự án." };
  if (!dir || !existsSync(dir) || !statSync(dir).isDirectory()) return { error: "Không có thư mục này trong dự án." };
  if ((dir + "\\").toLowerCase().startsWith(from.toLowerCase() + "\\")) return { error: "Không chuyển được thư mục vào chính nó." };
  const to = join(dir, basename(from));
  if (to.toLowerCase() === from.toLowerCase()) return { path: relOf(p, from) };
  if (existsSync(to)) return { error: `Thư mục đích đã có "${basename(from)}".` };
  renameSync(from, to);
  return { path: relOf(p, to) };
}

/**
 * Chỗ ghi một file kéo thả từ Windows: `rel` là đường dẫn tương đối của nó trong phần được thả (có thể gồm thư mục con).
 * Tạo thư mục con nếu cần; trùng tên file thì thêm " (2)", " (3)"… Trả null nếu đường dẫn ra ngoài dự án.
 */
export function uploadTarget(p: Project, parent: unknown, rel: unknown): string | null {
  const parts = typeof rel === "string" ? rel.split(/[\\/]/).filter(Boolean) : [];
  if (!parts.length || !parts.every(nameOk)) return null;
  const dir = inside(p, [typeof parent === "string" ? parent : "", ...parts.slice(0, -1)].filter(Boolean).join("/"));
  if (!dir) return null;
  mkdirSync(dir, { recursive: true });
  const name = parts[parts.length - 1], ext = extname(name), stem = basename(name, ext);
  let to = join(dir, name);
  for (let i = 2; existsSync(to); i++) to = join(dir, `${stem} (${i})${ext}`);
  return to;
}
export const relPath = relOf;

/** Dán: chép file/thư mục (trong dự án) vào thư mục đích; trùng tên thì thêm " - bản sao", " - bản sao (2)"… */
export function pasteEntry(p: Project, src: unknown, parent: unknown): { path: string } | { error: string } {
  const from = typeof src === "string" && src ? inside(p, src) : null;
  const dir = inside(p, typeof parent === "string" ? parent : "");
  if (!from || !existsSync(from)) return { error: "File cần dán không còn trong dự án." };
  if (!dir || !existsSync(dir) || !statSync(dir).isDirectory()) return { error: "Không có thư mục này trong dự án." };
  if (statSync(from).isDirectory() && (dir + "\\").toLowerCase().startsWith(from.toLowerCase() + "\\")) return { error: "Không dán được thư mục vào chính nó." };
  const ext = statSync(from).isDirectory() ? "" : extname(from), stem = basename(from, ext);
  let to = join(dir, basename(from));
  for (let i = 1; existsSync(to); i++) to = join(dir, `${stem} - bản sao${i > 1 ? ` (${i})` : ""}${ext}`);
  cpSync(from, to, { recursive: true, errorOnExist: true });
  return { path: relOf(p, to) };
}

/** Tìm file/thư mục theo tên (không phân biệt hoa thường) trong một thư mục của dự án, tối đa 200 kết quả. */
export function searchEntries(p: Project, path: unknown, q: unknown): Entry[] | { error: string } {
  const needle = typeof q === "string" ? q.trim().toLowerCase() : "";
  if (!needle) return { error: "Nhập chữ cần tìm." };
  const root = inside(p, typeof path === "string" ? path : "");
  if (!root || !existsSync(root) || !statSync(root).isDirectory()) return { error: "Không có thư mục này trong dự án." };
  const out: Entry[] = [];
  const walk = (d: string) => {
    for (const e of readdirSync(d, { withFileTypes: true })) {
      if (out.length >= 200 || HIDDEN.has(e.name)) continue;
      const full = join(d, e.name);
      try {
        const st = statSync(full);
        if (e.name.toLowerCase().includes(needle)) out.push({ name: e.name, path: relOf(p, full), dir: st.isDirectory(), size: st.size, mtime: st.mtimeMs });
        if (st.isDirectory()) walk(full);
      } catch { /* bỏ qua mục không đọc được */ }
    }
  };
  walk(root);
  return out;
}

/** Tạo file trống hoặc thư mục trong thư mục dự án (menu chuột phải ở cột file). */
export function createEntry(p: Project, parent: unknown, name: unknown, kind: "file" | "dir"): { path: string } | { error: string } {
  const n = typeof name === "string" ? name.trim() : "";
  if (!nameOk(n)) return { error: BAD_MSG };
  const dir = inside(p, typeof parent === "string" ? parent : "");
  if (!dir || !existsSync(dir) || !statSync(dir).isDirectory()) return { error: "Không có thư mục này trong dự án." };
  const full = join(dir, n);
  if (existsSync(full)) return { error: `Đã có "${n}" trong thư mục này.` };
  if (kind === "dir") mkdirSync(full); else writeFileSync(full, "", { flag: "wx" });
  return { path: relative(resolve(p.dir!), full).replace(/\\/g, "/") };
}

