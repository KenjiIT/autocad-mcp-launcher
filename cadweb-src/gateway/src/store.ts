import { createHash } from "node:crypto";
import { cleanUsage, type Usage } from "./usage.js";
import { existsSync, mkdirSync, readdirSync, readFileSync, renameSync, rmSync, rmdirSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join } from "node:path";

// Dữ liệu cục bộ: gateway/data/ (nằm trong .gitignore). Mọi dữ liệu thuộc về một "phạm vi" (Scope):
//   data/users/<userId>/{conversations,images,cli-sessions.json}
// Phạm vi hiện chỉ là một tài khoản. Khi có dự án dùng chung, thêm { kind: "project" } -> data/projects/<id>/...
// cùng bộ hàm này, với bước kiểm thành viên đặt ở route trước khi gọi vào đây.
const ROOT = process.env.CAD_DATA_DIR ?? fileURLToPath(new URL("../data/", import.meta.url));

export type Scope = { kind: "user" | "project"; id: string };
export const userScope = (id: string): Scope => {
  if (!/^[a-z0-9-]{1,64}$/.test(id)) throw new Error("userId không hợp lệ");   // chặn ../ và ký tự lạ trong tên thư mục
  return { kind: "user", id };
};
const dirOf = (s: Scope) => join(ROOT, `${s.kind}s`, s.id);
const convDir = (s: Scope) => { const d = join(dirOf(s), "conversations"); mkdirSync(d, { recursive: true }); return d; };
const imgDir = (s: Scope) => { const d = join(dirOf(s), "images"); mkdirSync(d, { recursive: true }); return d; };

/** Xóa toàn bộ dữ liệu của một phạm vi (hội thoại, ảnh, phiên CLI). Chỉ xóa trong data/<loại>s/<id> do userScope đã kiểm tra. */
export const removeScopeData = (s: Scope) => rmSync(dirOf(s), { recursive: true, force: true });

export const validId = (s: string) => /^[a-zA-Z0-9-]{8,64}$/.test(s);
export const validFile = (s: string) => /^[a-f0-9]{16,64}\.(png|jpg|webp|gif)$/.test(s);
const EXT: Record<string, string> = { "image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "image/gif": "gif" };
const MIME: Record<string, string> = { png: "image/png", jpg: "image/jpeg", webp: "image/webp", gif: "image/gif" };

export type Conversation = {
  id: string; title: string; createdAt: number; updatedAt: number; engine: string;
  sessionId?: string; model?: string; usage?: Usage; history: unknown[]; items: unknown[];
};

function saveImage(scope: Scope, b64: string, mime: string): string | null {
  const ext = EXT[mime]; if (!ext) return null;
  const name = createHash("sha256").update(b64).digest("hex").slice(0, 32) + "." + ext;
  const p = join(imgDir(scope), name);
  if (!existsSync(p)) writeFileSync(p, Buffer.from(b64, "base64"));
  return name;
}

/** Tách ảnh base64 ra file. `items` (hiển thị) -> url; `history` (gửi lại cho Claude) -> ghi chú chữ. */
function strip(scope: Scope, node: any, forHistory: boolean): any {
  if (Array.isArray(node)) return node.map(n => strip(scope, n, forHistory));
  if (node && typeof node === "object") {
    if (node.type === "image") {
      const data = node.data ?? node.source?.data, mime = node.mimeType ?? node.source?.media_type;
      if (typeof data === "string") {
        const name = saveImage(scope, data, mime);
        if (forHistory) return { type: "text", text: "[ảnh đã lược bỏ khi lưu]" };
        return name ? { type: "image", mimeType: mime, url: `/api/files/${name}` } : { type: "text", text: "[ảnh không hỗ trợ]" };
      }
    }
    return Object.fromEntries(Object.entries(node).map(([k, v]) => [k, strip(scope, v, forHistory)]));
  }
  return node;
}

const file = (scope: Scope, id: string) => join(convDir(scope), `${id}.json`);

export function listConversations(scope: Scope) {
  const d = convDir(scope);
  return readdirSync(d).filter(f => f.endsWith(".json")).flatMap(f => {
    try {
      const c = JSON.parse(readFileSync(join(d, f), "utf8")) as Conversation;
      return [{ id: c.id, title: c.title, updatedAt: c.updatedAt, engine: c.engine, model: c.model }];
    } catch { return []; }
  }).sort((a, b) => b.updatedAt - a.updatedAt);
}

export function getConversation(scope: Scope, id: string): Conversation | null {
  try { return JSON.parse(readFileSync(file(scope, id), "utf8")); } catch { return null; }
}

export function putConversation(scope: Scope, id: string, b: Partial<Conversation>): Conversation {
  const old = getConversation(scope, id);
  const now = Date.now();
  const c: Conversation = {
    id, createdAt: old?.createdAt ?? now, updatedAt: now,
    title: String(b.title ?? old?.title ?? "Cuộc trò chuyện mới").slice(0, 120),
    engine: String(b.engine ?? old?.engine ?? "cli"),
    sessionId: b.sessionId ?? old?.sessionId,
    model: typeof b.model === "string" && b.model ? b.model.slice(0, 64) : old?.model,
    usage: b.usage !== undefined ? cleanUsage(b.usage) : old?.usage,
    history: b.history !== undefined ? strip(scope, b.history, true) : old?.history ?? [],
    items: b.items !== undefined ? strip(scope, b.items, false) : old?.items ?? [],
  };
  const f = file(scope, id), tmp = f + ".tmp";
  writeFileSync(tmp, JSON.stringify(c)); renameSync(tmp, f); // ghi nguyên tử, tránh hỏng file khi dừng giữa chừng
  return c;
}

export const deleteConversation = (scope: Scope, id: string) => rmSync(file(scope, id), { force: true });
export const readImage = (scope: Scope, name: string) => {
  try { return { data: readFileSync(join(imgDir(scope), name)), mime: MIME[name.split(".").pop()!] }; } catch { return null; }
};

// ---- Phiên Claude CLI: chỉ được nối tiếp phiên do chính phạm vi này tạo ra (không nhận session_id tùy ý từ trình duyệt) ----
const cliFile = (s: Scope) => { mkdirSync(dirOf(s), { recursive: true }); return join(dirOf(s), "cli-sessions.json"); };
const cliSet = (s: Scope): string[] => { try { return JSON.parse(readFileSync(cliFile(s), "utf8")); } catch { return []; } };
export const ownsCliSession = (s: Scope, sid: string) => cliSet(s).includes(sid);
export function rememberCliSession(s: Scope, sid: string) {
  const cur = cliSet(s);
  if (!cur.includes(sid)) writeFileSync(cliFile(s), JSON.stringify([...cur, sid]));
}

/**
 * Dữ liệu cũ (trước khi có tài khoản) nằm chung ở data/conversations và data/images. Giao hết cho phạm vi được gọi
 * (route chỉ gọi cho quản trị viên) rồi xóa thư mục cũ. Chạy lại không làm gì khi đã giao xong.
 */
export function adoptLegacy(scope: Scope): number {
  const lc = join(ROOT, "conversations"), li = join(ROOT, "images");
  let n = 0;
  if (existsSync(lc)) {
    for (const f of readdirSync(lc).filter(f => f.endsWith(".json"))) {
      const to = join(convDir(scope), f);
      if (existsSync(to)) continue;
      try { const sid = JSON.parse(readFileSync(join(lc, f), "utf8")).sessionId; if (typeof sid === "string") rememberCliSession(scope, sid); } catch { /* file hỏng vẫn chuyển */ }
      renameSync(join(lc, f), to); n++;
    }
  }
  if (existsSync(li)) for (const f of readdirSync(li)) { const to = join(imgDir(scope), f); if (!existsSync(to)) renameSync(join(li, f), to); }
  for (const d of [lc, li]) { try { rmdirSync(d); } catch { /* còn file lạ: để nguyên */ } }
  return n;
}
