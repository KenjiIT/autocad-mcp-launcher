export type Content = { type: string; text?: string; data?: string; mimeType?: string; url?: string };

/** Lỗi mạng/HTTP phía trình duyệt thành câu dễ hiểu. */
export function niceError(e: unknown): string {
  const m = (e as Error)?.message ?? String(e);
  if (/Failed to fetch|NetworkError|Load failed/i.test(m)) return "Không liên lạc được với gateway. Kiểm tra gateway đang chạy (npm run dev:gateway).";
  if (/^HTTP 5/.test(m)) return `Gateway gặp lỗi (${m}). Xem cửa sổ chạy gateway để biết chi tiết.`;
  return m;
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, { ...init, headers: { "Content-Type": "application/json" } });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.error ?? `HTTP ${r.status}`);
  return j as T;
}

/** Ba cửa sổ hạn mức chạy song song (không dùng ở bản local: /api/quota không tồn tại nên luôn rơi về null). */
export type Win = "h5" | "week" | "month";
export type WinState = { win: Win; used: number; limit: number | null; resetAt: number };
export const WIN_NAME: Record<Win, string> = { h5: "5 giờ", week: "tuần", month: "tháng" };
export type Quota = { wins: WinState[] };
// Bản local không có hạn mức theo tài khoản (đã thay bằng hạn mức gói ở thanh "Đã sử dụng"): không gọi gateway.
export const getQuota = (): Promise<Quota> => Promise.reject(new Error("không có hạn mức tài khoản"));
export const tightest = (wins: WinState[]): WinState | null =>
  wins.filter(w => w.limit).sort((a, b) => b.used / b.limit! - a.used / a.limit!)[0] ?? null;

export type Health = { ok: boolean; tools: number; servers: { id: string; name: string; ok: boolean; tools: number; error?: string }[] };
export const health = () => req<Health>("/api/health");

export type ChatEvent =
  | { event: "text"; data: string }
  | { event: "tool_use"; data: { id: string; name: string; input: unknown } }
  | { event: "tool_result"; data: { id: string; isError: boolean; content?: Content[] } }
  | { event: "notice" | "error"; data: string }
  | { event: "usage"; data: Usage }
  | { event: "ask"; data: { id: string; questions: AskQuestion[] } }
  | { event: "done"; data: { messages: unknown[]; sessionId?: string } };

/** Bảng lựa chọn khi agent hỏi (tool ask_user). */
export type AskQuestion = { question: string; header: string; multiSelect: boolean; options: { label: string; description?: string }[] };
export type AskAnswer = { selected: string[]; other?: string };
export const answerAsk = (id: string, answers: AskAnswer[]) =>
  req<{ ok: boolean }>(`/api/ask/${id}`, { method: "POST", body: JSON.stringify({ answers }) });

/** Token của phiên chat. cacheRead/cacheWrite là phần đầu vào đọc từ / ghi vào bộ nhớ đệm; costUsd chỉ có khi chạy bằng Claude CLI. */
export type Usage = { input: number; output: number; cacheRead: number; cacheWrite: number; costUsd?: number };
export const NO_USAGE: Usage = { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 };
export const addUsage = (a: Usage, b: Usage): Usage => ({
  input: a.input + b.input, output: a.output + b.output, cacheRead: a.cacheRead + b.cacheRead, cacheWrite: a.cacheWrite + b.cacheWrite,
  ...((a.costUsd ?? 0) + (b.costUsd ?? 0) > 0 ? { costUsd: (a.costUsd ?? 0) + (b.costUsd ?? 0) } : {}),
});

/** POST /api/chat, đọc luồng SSE, gọi onEvent cho từng sự kiện. */
export async function chat(messages: unknown[], sessionId: string | undefined, onEvent: (e: ChatEvent) => void, signal: AbortSignal, model?: string, effort?: string) {
  const r = await fetch("/api/chat", {
    method: "POST", signal,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages, sessionId, model, effort, project: currentProject }),
  });
  if (!r.ok || !r.body) throw new Error((await r.json().catch(() => ({}))).error ?? `HTTP ${r.status}`);
  const reader = r.body.pipeThrough(new TextDecoderStream()).getReader();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += value.replace(/\r\n/g, "\n");
    let i: number;
    while ((i = buf.indexOf("\n\n")) >= 0) {
      const block = buf.slice(0, i); buf = buf.slice(i + 2);
      const ev = /^event: (.*)$/m.exec(block)?.[1];
      const data = block.split("\n").filter(l => l.startsWith("data: ")).map(l => l.slice(6)).join("\n");
      if (ev && data) onEvent({ event: ev, data: JSON.parse(data) } as ChatEvent);
    }
  }
}

export type Config = { engine: "cli" | "api" | "codex"; cliVersion: string | null; codexVersion: string | null; keySet: boolean; keyHint: string; keySource: "file" | "env" | "none"; model: string };
export const getConfig = () => req<Config>("/api/config");
export const saveConfig = (p: { anthropicKey?: string; engine?: "cli" | "api" | "codex" }) =>
  req<Config>("/api/config", { method: "PUT", body: JSON.stringify(p) });

export type ConvMeta = { id: string; title: string; updatedAt: number; engine: string; model?: string };
export type ModelInfo = { id: string; label: string; legacy?: boolean };
/** Model người dùng được chọn cho từng phiên, và model mặc định (CHAT_MODEL hoặc Sonnet 5.5). */
export const listModels = () => req<{ models: ModelInfo[]; default: string }>("/api/models");
export type Conv = ConvMeta & { sessionId?: string; usage?: Usage; history: unknown[]; items: unknown[] };
export const listConvs = (project?: string) => req<{ conversations: ConvMeta[] }>(`/api/conversations?project=${encodeURIComponent(project ?? currentProject)}`).then(r => r.conversations);
export const getConv = (id: string) => req<Conv>(`/api/conversations/${id}${pq("?")}`);
export const putConv = (id: string, body: Partial<Conv>) =>
  req<ConvMeta>(`/api/conversations/${id}${pq("?")}`, { method: "PUT", body: JSON.stringify(body) });
export const delConv = (id: string) => req<{ ok: boolean }>(`/api/conversations/${id}${pq("?")}`, { method: "DELETE" });

/** Ảnh lưu trên gateway. */
export async function fetchImage(url: string): Promise<string> {
  const r = await fetch(url.startsWith("/api/files/") ? url + pq(url.includes("?") ? "&" : "?") : url);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return URL.createObjectURL(await r.blob());
}
export const newId = (): string => (crypto.randomUUID?.() ?? `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`);

export type Skill = { name: string; description: string };
export const listSkills = () => req<{ skills: Skill[] }>("/api/skills").then(r => r.skills);

export type ClaudeStatus = { installed: boolean; version: string | null; loggedIn: boolean; email: string | null; installing: boolean; installError: string | null };
export const claudeStatus = () => req<ClaudeStatus>("/api/claude/status");
export const claudeInstall = () => req<{ ok: boolean }>("/api/claude/install", { method: "POST" });
export const claudeLogin = () => req<{ ok: boolean }>("/api/claude/login", { method: "POST" });

/** Dự án kiểu Orca: mỗi dự án là một thư mục trên máy; hội thoại lưu riêng theo dự án. Rỗng = dự án đầu tiên. */
export type Project = { id: string; name: string; dir: string | null; createdAt: number; pinned?: boolean };
let currentProject = "";
export const setCurrentProject = (id: string) => { currentProject = id; };
const pq = (sep: string) => `${sep}project=${encodeURIComponent(currentProject)}`;
export const listProjects = () => req<{ projects: Project[] }>("/api/projects").then(r => r.projects);
export const createProject = (name: string, dir: string) =>
  req<{ project: Project }>("/api/projects", { method: "POST", body: JSON.stringify({ name, dir }) }).then(r => r.project);
export const renameProject = (id: string, name: string) =>
  req<{ project: Project }>(`/api/projects/${id}`, { method: "PATCH", body: JSON.stringify({ name }) }).then(r => r.project);
export const pinProject = (id: string, pinned: boolean) =>
  req<{ project: Project }>(`/api/projects/${id}`, { method: "PATCH", body: JSON.stringify({ pinned }) }).then(r => r.project);
export const deleteProject = (id: string) => req<{ ok: boolean }>(`/api/projects/${id}`, { method: "DELETE" });

/** Hộp chọn thư mục/file của Windows, mở trên máy chạy gateway. Hủy thì null/rỗng. */
export const pickFolder = () => req<{ path: string | null }>("/api/pick/folder", { method: "POST" }).then(r => r.path);
export const pickFiles = () => req<{ paths: string[] }>("/api/pick/files", { method: "POST" }).then(r => r.paths);
export const importFiles = (id: string, paths: string[]) =>
  req<{ copied: string[] }>(`/api/projects/${id}/import`, { method: "POST", body: JSON.stringify({ paths }) }).then(r => r.copied);
export type Entry = { name: string; path: string; dir: boolean; size: number; mtime: number };
export const listProjectFiles = (id: string, path = "") =>
  req<{ entries: Entry[]; dir: string | null }>(`/api/projects/${id}/files?path=${encodeURIComponent(path)}`);
export const revealFile = (id: string, path = "") => req<{ ok: boolean }>(`/api/projects/${id}/reveal`, { method: "POST", body: JSON.stringify({ path }) });
export const rawUrl = (id: string, path: string) => `/api/projects/${id}/raw?path=${encodeURIComponent(path)}`;
export const newEntry = (id: string, parent: string, name: string, kind: "file" | "dir") =>
  req<{ path: string }>(`/api/projects/${id}/new`, { method: "POST", body: JSON.stringify({ parent, name, kind }) }).then(r => r.path);
export const trashEntry = (id: string, path: string) => req<{ ok: boolean }>(`/api/projects/${id}/trash`, { method: "POST", body: JSON.stringify({ path }) });
const fileOp = <T,>(id: string, op: string, body: object) => req<T>(`/api/projects/${id}/${op}`, { method: "POST", body: JSON.stringify(body) });
export const renameEntry = (id: string, path: string, name: string) => fileOp<{ path: string }>(id, "rename", { path, name });
export const pasteEntry = (id: string, src: string, parent: string) => fileOp<{ path: string }>(id, "paste", { src, parent });
export const searchEntries = (id: string, path: string, q: string) => fileOp<{ entries: Entry[] }>(id, "search", { path, q }).then(r => r.entries);
export const launchEntry = (id: string, path: string, how: "default" | "choose") => fileOp<{ ok: boolean }>(id, "launch", { path, with: how });
export type PlanWin = { key: string; label: string; used: number; resetsAt: number | null };
export type PlanSide = { plan: string | null; windows: PlanWin[]; at: number } | null;
export type PlanUsage = { claude: PlanSide; codex: PlanSide };
export const getPlanUsage = () => req<PlanUsage>("/api/plan-usage");
export const refreshPlanUsage = () => req<PlanUsage>("/api/plan-usage/refresh", { method: "POST" });
export const moveEntry = (id: string, src: string, parent: string) => fileOp<{ path: string }>(id, "move", { src, parent });
/** Chép một file kéo thả từ máy vào thư mục `parent` của dự án; `rel` có thể gồm thư mục con (khi thả cả thư mục). */
export async function uploadFile(id: string, parent: string, rel: string, file: Blob): Promise<string> {
  const r = await fetch(`/api/projects/${id}/upload?parent=${encodeURIComponent(parent)}&rel=${encodeURIComponent(rel)}`, { method: "POST", body: file });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.error ?? `HTTP ${r.status}`);
  return j.path;
}

/** Bấm vào file ở cột file thì làm gì (người dùng chọn trong Cài đặt; lưu trên trình duyệt này). */
export type ClickAction = "default" | "choose" | "web";
export const getClickAction = (): ClickAction => { try { const v = localStorage.getItem("cad-file-click"); return v === "choose" || v === "web" ? v : "default"; } catch { return "default"; } };
export const setClickAction = (v: ClickAction) => { try { localStorage.setItem("cad-file-click", v); } catch { /* bỏ qua */ } };
