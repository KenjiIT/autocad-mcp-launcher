import { existsSync, readFileSync, writeFileSync, chmodSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { DEFAULT_CODEX_MODEL, codexCatalog } from "./codexmodels.js";

// File cấu hình cục bộ cạnh package gateway (đã nằm trong .gitignore). Ưu tiên hơn biến môi trường.
const FILE = process.env.CAD_CONFIG_FILE ?? fileURLToPath(new URL("../.config.json", import.meta.url));   // CAD_CONFIG_FILE chỉ để chạy thử

export type McpServer = {
  id: string; name: string; enabled: boolean; transport: "http" | "stdio";
  url?: string; token?: string;                       // http
  command?: string; args?: string[]; env?: Record<string, string>; // stdio
};

type Saved = { anthropicKey?: string; model?: string; engine?: string };
let saved: Saved = {};
try { if (existsSync(FILE)) saved = JSON.parse(readFileSync(FILE, "utf8")); } catch { /* file hỏng: bỏ qua */ }

function write() {
  writeFileSync(FILE, JSON.stringify(saved, null, 2), { mode: 0o600 });
  try { chmodSync(FILE, 0o600); } catch { /* Windows */ }
}

export const getKey = () => saved.anthropicKey || process.env.ANTHROPIC_API_KEY || "";
/** Model mặc định cho cuộc trò chuyện mới: biến CHAT_MODEL, hoặc Sonnet 5.5. Người dùng chọn model riêng cho từng phiên. */
export type Engine = "cli" | "api" | "codex";
export const getEngine = (): Engine => { const e = saved.engine || process.env.CHAT_ENGINE; return e === "api" || e === "codex" ? e : "cli"; };
/** Engine của một phiên chat (người dùng chọn lúc tạo phiên); giá trị lạ thì dùng engine mặc định trong Cài đặt. */
export const engineFor = (v: unknown): Engine => (v === "cli" || v === "api" || v === "codex" ? v : getEngine());
export const getModel = (engine: Engine = getEngine()) => (engine === "codex" ? DEFAULT_CODEX_MODEL : process.env.CHAT_MODEL || "claude-sonnet-5-5");

/** Model người dùng được chọn cho từng phiên. CHAT_MODELS="id:Nhãn,id2:Nhãn 2" để đổi danh sách. */
const DEFAULT_MODELS: [string, string][] = [
  ["claude-opus-5-5", "Claude Opus 5.5 (Cho việc phức tạp và việc hằng ngày)"],
  ["claude-fable-5-2", "Claude Fable 5.2 (Cho việc khó nhất)"],
  ["claude-sonnet-5-5", "Claude Sonnet 5.5 (Tiết kiệm nhất cho việc đơn giản)"],
  ["claude-haiku-5-5", "Claude Haiku 5.5 (Nhanh nhất cho câu trả lời ngắn)"],
];
/** Model đời trước, vẫn gọi được qua Claude CLI (đã thử từng tên trên máy). Hiện thành nhóm riêng trong ô chọn. */
const LEGACY_MODELS: [string, string][] = [
  ["claude-fable-5-1", "Claude Fable 5.1"], ["claude-fable-5", "Claude Fable 5"],
  ["claude-opus-5", "Claude Opus 5"], ["claude-sonnet-5", "Claude Sonnet 5"],
  ["claude-opus-4-7", "Claude Opus 4.7"], ["claude-opus-4-6", "Claude Opus 4.6"], ["claude-sonnet-4-6", "Claude Sonnet 4.6"],
  ["claude-opus-4-5", "Claude Opus 4.5"], ["claude-haiku-4-5", "Claude Haiku 4.5"], ["claude-opus-4-1", "Claude Opus 4.1"],
];
export function getModels(engine: Engine = getEngine()): { id: string; label: string; legacy?: boolean }[] {
  // Codex: model mặc định của Codex, kèm các model trong danh mục của chính Codex (tải bằng `codex debug models`)
  if (engine === "codex") return [{ id: DEFAULT_CODEX_MODEL, label: "Mặc định của Codex" }, ...codexCatalog()];
  const fromEnv = (process.env.CHAT_MODELS ?? "").split(",").map(x => x.trim()).filter(Boolean)
    .map(x => { const i = x.indexOf(":"); return (i > 0 ? [x.slice(0, i).trim(), x.slice(i + 1).trim()] : [x, x]) as [string, string]; })
    .filter(([id]) => /^[a-z0-9][a-z0-9._-]{1,63}$/i.test(id));
  const list: { id: string; label: string; legacy?: boolean }[] = fromEnv.length ? fromEnv.map(([id, label]) => ({ id, label }))
    : [...DEFAULT_MODELS.map(([id, label]) => ({ id, label })), ...LEGACY_MODELS.map(([id, label]) => ({ id, label, legacy: true }))];
  const def = getModel(engine);
  return list.some(m => m.id === def) ? list : [{ id: def, label: def }, ...list];   // model mặc định do admin đặt luôn có trong danh sách
}
/** Model dùng cho một lượt chat: lấy theo lựa chọn của phiên nếu nằm trong danh sách cho phép, ngược lại dùng mặc định. */
/** Mức cố gắng (suy nghĩ) cho một lượt chat; giá trị lạ thì bỏ qua để CLI dùng mặc định. */
export const EFFORTS = ["low", "medium", "high", "xhigh", "max"] as const;
export type Effort = typeof EFFORTS[number];
export const effortFor = (v: unknown): Effort | undefined => (EFFORTS as readonly unknown[]).includes(v) ? v as Effort : undefined;
export const modelFor = (requested?: unknown, engine: Engine = getEngine()) =>
  (typeof requested === "string" && getModels(engine).some(m => m.id === requested) ? requested : getModel(engine));

export function saveConfig(patch: { anthropicKey?: string; engine?: string }) {
  for (const [k, v] of Object.entries(patch) as [keyof typeof patch, string | undefined][]) {
    if (v === undefined) continue;
    if (v === "") delete saved[k]; else saved[k] = v.trim();
  }
  write();
}

const mask = (k: string) => (k ? `${k.slice(0, 7)}…${k.slice(-4)}` : "");
export const publicConfig = () => ({
  engine: getEngine(), keySet: !!getKey(), keyHint: mask(getKey()), model: getModel(),
  keySource: saved.anthropicKey ? "file" : process.env.ANTHROPIC_API_KEY ? "env" : "none",
});

