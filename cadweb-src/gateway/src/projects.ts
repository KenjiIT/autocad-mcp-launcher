import { randomBytes } from "node:crypto";
import { closeSync, copyFileSync, cpSync, rmSync, existsSync, mkdirSync, openSync, readdirSync, readFileSync, renameSync, statSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { fileURLToPath } from "node:url";
import { basename, dirname, extname, isAbsolute, join, relative, resolve } from "node:path";
import { LOCAL_DIR, listConversations, mergeInto, putConversation, removeScopeData, type Scope } from "./store.js";

// Dự án kiểu Orca: mỗi dự án là MỘT THƯ MỤC trên máy. Hội thoại và ảnh của dự án lưu trong chính thư mục đó (<dir>/.cadstudio/),
// còn Claude CLI / Codex chạy với thư mục làm việc là thư mục dự án và được đọc/ghi file trong đó.
// Luôn có ít nhất một dự án: máy mới tự có dự án "master" kèm một phiên chat.
const DATA = process.env.CAD_DATA_DIR ?? fileURLToPath(new URL("../data/", import.meta.url));
const FILE = join(DATA, "projects.json");
export const PROJECTS_ROOT = process.env.CAD_PROJECTS_DIR ?? join(homedir(), "CAD Studio", "projects");
export const STARTER_TITLE = "Phiên chat mới";

export type Project = { id: string; name: string; dir: string | null; createdAt: number; pinned?: boolean; shell?: boolean };   // shell: cho agent chạy lệnh (Bash) trong thư mục dự án

const load = (): Project[] => { try { return JSON.parse(readFileSync(FILE, "utf8")); } catch { return []; } };
const save = (list: Project[]) => { mkdirSync(DATA, { recursive: true }); writeFileSync(FILE + ".tmp", JSON.stringify(list, null, 2)); renameSync(FILE + ".tmp", FILE); };
const scopeFor = (p: Project): Scope => ({ kind: "project", id: p.id, dir: p.dir ?? undefined });

/** Một phiên chat trống để dự án mới có sẵn chỗ bắt đầu (hiện ngay trong cây dự án). */
const addStarter = (p: Project) => putConversation(scopeFor(p), randomBytes(8).toString("hex"), { title: STARTER_TITLE, items: [], history: [] });

/**
 * Chuyển một lần dữ liệu cũ trong thư mục app sang .cadstudio/ của dự án:
 *   data/projects/<id>  -> dự án <id> (nếu còn và có thư mục), không thì dự án mặc định (đầu danh sách);
 *   data/users/<x>      -> dự án mặc định (chat từ trước khi có dự án).
 * mergeInto chỉ xóa thư mục cũ sau khi đã chép đủ. Lỗi (ổ đĩa rút, thư mục dự án mất…) thì để nguyên, lần sau thử lại.
 */
function migrateLegacy(list: Project[]) {
  const def = list.find(p => p.dir && existsSync(p.dir));
  for (const kind of ["projects", "users"] as const) {
    const base = join(DATA, kind);
    if (!existsSync(base)) continue;
    for (const id of readdirSync(base)) {
      const own = kind === "projects" ? list.find(p => p.id === id && p.dir && existsSync(p.dir)) : undefined;
      const known = kind === "projects" && list.some(p => p.id === id);
      if (known && !own) continue;   // dự án không thư mục (dữ liệu ở lại thư mục app) hoặc thư mục đang vắng (thử lại lần sau)
      const target = own ?? def;
      if (!target) continue;
      try {
        // Phiên Claude CLI của chat "Chung" cũ chạy ở thư mục tạm, không nối tiếp được trong thư mục dự án.
        if (kind === "users") rmSync(join(base, id, "cli-sessions.json"), { force: true });
        const n = mergeInto(join(base, id), scopeFor(target));
        if (n) console.log(`chuyển ${n} hội thoại từ data/${kind}/${id} sang ${join(target.dir!, LOCAL_DIR)}`);
      } catch (e: any) { console.error(`không chuyển được data/${kind}/${id}:`, e?.message ?? e); }
    }
  }
}

/** Máy mới: tạo dự án "master" + một phiên chat. Lần đầu chạy bản mới thì chuyển chat cũ sang .cadstudio/ của dự án. */
let migrated = false;
function ensureDefault(): Project[] {
  let list = load();
  if (!list.length) {
    const dir = join(PROJECTS_ROOT, "master");
    mkdirSync(dir, { recursive: true });
    list = [{ id: randomBytes(6).toString("hex"), name: "master", dir, createdAt: Date.now() }];
    save(list);
  }
  if (!migrated) {
    migrated = true;
    migrateLegacy(list);
    const first = list[0];
    if (first.dir && existsSync(first.dir) && !listConversations(scopeFor(first)).length) addStarter(first);
  }
  return list;
}

/** Dự án ghim lên đầu, còn lại giữ thứ tự tạo. */
export const listProjects = (): Project[] => { const l = ensureDefault(); return [...l.filter(p => p.pinned), ...l.filter(p => !p.pinned)]; };
/** Không nêu dự án (hoặc nêu dự án đã xóa) thì null; route tự báo lỗi. Bỏ trống id thì là dự án đầu tiên. */
export const getProject = (id: string | undefined | null): Project | undefined => { const l = listProjects(); return id ? l.find(p => p.id === id) : l[0]; };

/** Phạm vi lưu hội thoại của một dự án; dự án không tồn tại thì null. */
export function scopeOf(id: string | undefined | null): Scope | null {
  const p = getProject(id);
  return p ? scopeFor(p) : null;
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
  // Thư mục đã từng mở trong CAD Studio (có .cadstudio/ với chat cũ, vd. sau khi cài lại app): giữ nguyên, không thêm phiên trống.
  if (!listConversations(scopeFor(project)).length) addStarter(project);
  return { project };
}

/**
 * "Mở dự án có sẵn": thư mục đã là dự án thì trả lại dự án đó (existed), không tạo trùng.
 * Chưa là dự án thì tạo với tên = tên thư mục (trùng tên thì thêm số). sessions = số phiên chat sẵn có trong .cadstudio/.
 */
export function openProject(dir: unknown): { project: Project; existed: boolean; sessions: number } | { error: string } {
  const raw = typeof dir === "string" ? dir.trim() : "";
  if (!raw || !isAbsolute(raw)) return { error: "Thư mục phải là đường dẫn đầy đủ, ví dụ D:\\Du an\\Toa A." };
  const folder = resolve(raw);
  if (!existsSync(folder) || !statSync(folder).isDirectory()) return { error: "Không thấy thư mục này trên máy." };
  const list = listProjects();
  const same = list.find(p => p.dir && resolve(p.dir).toLowerCase() === folder.toLowerCase());
  if (same) return { project: same, existed: true, sessions: listConversations(scopeFor(same)).length };
  const cd = join(folder, LOCAL_DIR, "conversations");   // đếm chat cũ trong .cadstudio/ mà không tạo gì trong thư mục
  const sessions = existsSync(cd) ? readdirSync(cd).filter(f => f.endsWith(".json")).length : 0;
  const stem = (basename(folder) || "Dự án").slice(0, 70);
  let name = stem;
  for (let i = 2; list.some(p => p.name.toLowerCase() === name.toLowerCase()); i++) name = `${stem} (${i})`;
  const r = createProject(name, folder);
  return "error" in r ? r : { project: r.project, existed: false, sessions };
}

/** Tìm thư mục theo TÊN (kéo thả từ Explorer, trình duyệt không cho đường dẫn) ở vài chỗ quen thuộc, sâu 2 cấp. */
export function locateFolder(name: unknown, roots: string[] = defaultRoots()): string[] {
  const n = typeof name === "string" ? name.trim() : "";
  if (!n || /[\/]/.test(n) || n === "." || n === "..") return [];
  const out = new Set<string>();
  const walk = (d: string, depth: number) => {
    let ents: import("node:fs").Dirent[];
    try { ents = readdirSync(d, { withFileTypes: true }); } catch { return; }
    for (const e of ents) {
      if (!e.isDirectory() || e.name.startsWith(".") || e.name === "node_modules") continue;
      const full = join(d, e.name);
      if (e.name.toLowerCase() === n.toLowerCase()) out.add(full);
      if (depth > 1 && out.size < 10) walk(full, depth - 1);
    }
  };
  for (const r of roots) if (existsSync(r)) walk(r, 2);
  return [...out];
}

function defaultRoots(): string[] {
  const h = homedir();
  return [PROJECTS_ROOT, join(h, "Desktop"), join(h, "Documents"), join(h, "Downloads"), join(h, "OneDrive", "Desktop"), join(h, "OneDrive", "Documents"), h];
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
/** Số file và dung lượng của thư mục dự án (dừng đếm ở ``cap`` file để không treo với thư mục rất lớn). */
export function folderStats(dir: string, cap = 200_000): { files: number; bytes: number; capped: boolean } {
  let files = 0, bytes = 0, capped = false;
  const walk = (d: string) => {
    if (capped) return;
    let ents: import("node:fs").Dirent[];
    try { ents = readdirSync(d, { withFileTypes: true }); } catch { return; }
    for (const e of ents) {
      const full = join(d, e.name);
      if (e.isSymbolicLink()) continue;
      if (e.isDirectory()) walk(full);
      else if (e.isFile()) {
        files++;
        try { bytes += statSync(full).size; } catch { /* file đang bị khoá vẫn đếm */ }
        if (files >= cap) { capped = true; return; }
      }
    }
  };
  if (existsSync(dir)) walk(dir);
  return { files, bytes, capped };
}

const norm = (p: string) => resolve(p).replace(/\\/g, "/").replace(/\/+$/, "").toLowerCase();
const isInside = (child: string, parent: string) => norm(child).startsWith(norm(parent) + "/");

/**
 * Lý do KHÔNG được xóa thư mục dự án (null = được xóa): ổ gốc, thư mục home, Desktop/Documents/Downloads,
 * thư mục CAD Studio/projects (hoặc cha của nó), thư mục chứa hay nằm trong thư mục dự án khác.
 * ``protectedDirs`` tách ra tham số để kiểm thử.
 */
export function deleteFolderProblem(p: Project, all: Project[], protectedDirs: string[] = defaultProtected()): string | null {
  if (!p.dir) return "Dự án này không gắn thư mục trên máy.";
  const dir = norm(p.dir);
  if (/^[a-z]:$/.test(dir) || resolve(p.dir) === resolve(p.dir, "..")) return "Thư mục dự án là ổ đĩa gốc; không xóa.";
  for (const d of protectedDirs) {
    if (dir === norm(d)) return `Thư mục ${p.dir} là thư mục hệ thống/quan trọng của tài khoản; không xóa.`;
    if (isInside(d, p.dir)) return `Thư mục ${p.dir} chứa ${d}; không xóa.`;
  }
  for (const o of all) {
    if (o.id === p.id || !o.dir) continue;
    if (norm(o.dir) === dir) return `Thư mục này cũng là của dự án "${o.name}"; không xóa.`;
    if (isInside(o.dir, p.dir)) return `Thư mục này chứa thư mục của dự án "${o.name}" (${o.dir}); không xóa.`;
    if (isInside(p.dir, o.dir)) return `Thư mục này nằm trong thư mục của dự án "${o.name}"; không xóa.`;
  }
  return null;
}

function defaultProtected(): string[] {
  const h = homedir();
  const out = [h, join(h, "Desktop"), join(h, "Documents"), join(h, "Downloads"), join(h, "OneDrive"),
    join(h, "OneDrive", "Desktop"), join(h, "OneDrive", "Documents"), PROJECTS_ROOT, dirname(PROJECTS_ROOT)];
  return out;
}

/** File đang bị chương trình khác giữ (không mở ghi được), tối đa ``max`` file. */
export function lockedFiles(dir: string, max = 5): string[] {
  const out: string[] = [];
  const walk = (d: string) => {
    if (out.length >= max) return;
    let ents: import("node:fs").Dirent[];
    try { ents = readdirSync(d, { withFileTypes: true }); } catch { return; }
    for (const e of ents) {
      if (out.length >= max) return;
      const full = join(d, e.name);
      if (e.isSymbolicLink()) continue;
      if (e.isDirectory()) { walk(full); continue; }
      try { const fd = openSync(full, "r+"); closeSync(fd); }
      catch (err: any) { if (err?.code === "EBUSY" || err?.code === "EPERM" || err?.code === "EACCES") out.push(full); }
    }
  };
  if (existsSync(dir)) walk(dir);
  return out;
}

export function deleteProject(id: string): boolean | "last" {
  const list = load();
  if (!list.some(p => p.id === id)) return false;
  if (list.length === 1) return "last";
  save(list.filter(p => p.id !== id));
  removeScopeData({ kind: "project", id });   // chỉ dữ liệu trong thư mục app; .cadstudio/ ở lại để mở lại dự án là thấy chat
  return true;
}

// ---- File trong thư mục dự án (cây file ở cột phải) ----
export type Entry = { name: string; path: string; dir: boolean; size: number; mtime: number };
const HIDDEN = new Set([".git", LOCAL_DIR, "node_modules", ".venv", "__pycache__"]);

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

