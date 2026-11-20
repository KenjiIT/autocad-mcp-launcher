import { execFile } from "node:child_process";

// Danh sách model của Codex lấy động từ `codex debug models` (chỉ model hiện trong danh sách), để không phải ghi cứng tên model.
export const DEFAULT_CODEX_MODEL = "codex-default";     // không truyền -m: Codex dùng model mặc định của chính nó
export const CODEX_BIN = process.env.CODEX_BIN ?? "codex";

type Entry = { id: string; label: string };
let cache: { at: number; list: Entry[] } | null = null;
let inflight: Promise<void> | null = null;
const TTL = 10 * 60_000;

/** Danh sách đã tải (rỗng nếu chưa tải được). */
export const codexCatalog = (): Entry[] => cache?.list ?? [];

/** Phân tích đầu ra JSON của `codex debug models`. Tách riêng để kiểm thử. */
export function parseCodexModels(raw: string): Entry[] {
  const d = JSON.parse(raw);
  const arr: any[] = Array.isArray(d) ? d : Array.isArray(d?.models) ? d.models : [];
  return arr.filter(m => m && m.visibility === "list" && typeof m.slug === "string" && /^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/.test(m.slug))
    .map(m => ({ id: m.slug, label: String(m.display_name || m.slug).slice(0, 60) }));
}

/** Tải lại danh sách nếu cũ hơn 10 phút. Lỗi (chưa cài Codex, chưa đăng nhập...) thì giữ danh sách cũ. */
export function ensureCodexModels(): Promise<void> {
  if (cache && Date.now() - cache.at < TTL) return Promise.resolve();
  inflight ??= new Promise<void>(res => {
    execFile(CODEX_BIN, ["debug", "models"], { timeout: 20_000, maxBuffer: 16 * 1024 * 1024, windowsHide: true }, (e, out) => {
      if (!e) { try { cache = { at: Date.now(), list: parseCodexModels(out) }; } catch { /* đầu ra lạ: bỏ qua */ } }
      inflight = null; res();
    });
  });
  return inflight;
}
