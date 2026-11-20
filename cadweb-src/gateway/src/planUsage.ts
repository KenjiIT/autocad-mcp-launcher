import { execFile, spawn } from "node:child_process";
import { existsSync, mkdirSync, readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { fileURLToPath } from "node:url";
import { join } from "node:path";
import { claudeBin } from "./claudeSetup.js";

// Hạn mức của GÓI tài khoản (Claude Pro/Max, ChatGPT Plus/Pro cho Codex), không phải token của CAD Studio.
// Claude CLI tự báo trong luồng stream-json (sự kiện rate_limit_event) ở mỗi lượt chat; Codex ghi rate_limits
// vào nhật ký phiên ~/.codex/sessions. Đọc hai nguồn đó, không gọi API riêng nào.
export type Win = { key: string; label: string; used: number; resetsAt: number | null };
export type PlanUsage = { claude: { plan: string | null; windows: Win[]; at: number } | null; codex: { plan: string | null; windows: Win[]; at: number } | null };

const DATA = process.env.CAD_DATA_DIR ?? fileURLToPath(new URL("../data/", import.meta.url));
const FILE = join(DATA, "plan-usage.json");
const LABEL: Record<string, string> = { five_hour: "5h", seven_day: "tuần", seven_day_opus: "Opus", seven_day_sonnet: "Sonnet", seven_day_fable: "Fable" };
const labelOf = (k: string) => LABEL[k] ?? k.replace(/^seven_day_/, "").replace(/_/g, " ");

let claude: PlanUsage["claude"] = null;
try { claude = JSON.parse(readFileSync(FILE, "utf8")).claude ?? null; } catch { /* chưa có */ }
const persist = () => { try { mkdirSync(DATA, { recursive: true }); writeFileSync(FILE, JSON.stringify({ claude })); } catch { /* bỏ qua */ } };

/** Gọi từ bộ đọc stream-json của Claude CLI mỗi khi gặp rate_limit_event. */
export function recordClaudeRate(info: any) {
  const wins = info?.unifiedWindows && typeof info.unifiedWindows === "object" ? info.unifiedWindows
    : info?.rateLimitType ? { [info.rateLimitType]: info } : null;
  if (!wins) return;
  const windows: Win[] = Object.entries(wins).flatMap(([k, w]: [string, any]) =>
    typeof w?.utilization === "number" ? [{ key: k, label: labelOf(k), used: Math.round(w.utilization * 100), resetsAt: typeof w.resetsAt === "number" ? w.resetsAt * 1000 : null }] : []);
  windows.sort((a, b) => (a.key === "five_hour" ? -1 : b.key === "five_hour" ? 1 : a.key === "seven_day" ? -1 : b.key === "seven_day" ? 1 : 0));
  claude = { plan: claude?.plan ?? null, windows, at: Date.now() };
  persist();
}

let planCache: { at: number; plan: string | null } | null = null;
function claudePlan(): Promise<string | null> {
  if (planCache && planCache.at > Date.now() - 600_000) return Promise.resolve(planCache.plan);
  return new Promise(res => execFile(claudeBin(), ["auth", "status"], { timeout: 10_000, windowsHide: true }, (e, out) => {
    let plan: string | null = null;
    try {
      const j = JSON.parse(String(out));
      const tier = String(j.planTier ?? j.subscriptionType ?? "");
      plan = tier ? tier.replace(/_/g, " ").replace(/^./, c => c.toUpperCase()) : null;   // "max_20x" -> "Max 20x"
    } catch { /* CLI cũ */ }
    planCache = { at: Date.now(), plan };
    res(plan);
  }));
}

/** rate_limits mới nhất trong nhật ký phiên Codex (tìm từ ngày gần nhất trở về trước). */
function codexUsage(): PlanUsage["codex"] {
  const root = join(process.env.CODEX_HOME ?? join(homedir(), ".codex"), "sessions");
  if (!existsSync(root)) return null;
  const desc = (d: string) => { try { return readdirSync(d).sort().reverse(); } catch { return []; } };
  const files: { f: string; t: number }[] = [];
  outer: for (const y of desc(root)) for (const m of desc(join(root, y))) for (const d of desc(join(root, y, m))) {
    for (const f of desc(join(root, y, m, d)).filter(x => x.endsWith(".jsonl"))) { const p = join(root, y, m, d, f); files.push({ f: p, t: statSync(p).mtimeMs }); }
    if (files.length >= 8) break outer;
  }
  files.sort((a, b) => b.t - a.t);
  for (const { f, t } of files) {
    const lines = readFileSync(f, "utf8").split("\n");
    for (let i = lines.length - 1; i >= 0; i--) {
      if (!lines[i].includes('"rate_limits"')) continue;
      try {
        const find = (o: any): any => o && typeof o === "object" ? (o.rate_limits ?? Object.values(o).map(find).find(Boolean)) : undefined;
        const rl = find(JSON.parse(lines[i]));
        if (!rl) continue;
        const win = (w: any, key: string, label: string): Win[] => typeof w?.used_percent === "number"
          ? [{ key, label, used: Math.round(w.used_percent), resetsAt: typeof w.resets_at === "number" ? w.resets_at * 1000 : null }] : [];
        return { plan: typeof rl.plan_type === "string" ? rl.plan_type : null, windows: [...win(rl.primary, "primary", "5h"), ...win(rl.secondary, "secondary", "tuần")], at: t };
      } catch { /* dòng hỏng */ }
    }
  }
  return null;
}

/** Khung đã qua giờ đặt lại thì coi như 0% (số lưu là của lần dùng trước). */
const fresh = (w: Win): Win => w.resetsAt && w.resetsAt < Date.now() ? { ...w, used: 0, resetsAt: null } : w;

export async function planUsage(): Promise<PlanUsage> {
  const plan = await claudePlan().catch(() => null);
  const cx = codexUsage();
  return {
    claude: claude ? { ...claude, plan, windows: claude.windows.map(fresh) } : null,
    codex: cx ? { ...cx, windows: cx.windows.map(fresh) } : null,
  };
}

/** Làm mới số của Claude ngay: một lượt Haiku cực ngắn, không tool, chỉ để nhận rate_limit_event (vẫn tính vào gói). */
export function probeClaude(): Promise<void> {
  return new Promise(resolve => {
    const p = spawn(claudeBin(), ["-p", "--output-format", "stream-json", "--verbose", "--tools", "", "--strict-mcp-config", "--model", "claude-haiku-5-5"],
      { windowsHide: true, stdio: ["pipe", "pipe", "ignore"] });
    let buf = "";
    p.stdout.setEncoding("utf8").on("data", d => {
      buf += d; let i: number;
      while ((i = buf.indexOf("\n")) >= 0) {
        const line = buf.slice(0, i); buf = buf.slice(i + 1);
        try { const ev = JSON.parse(line); if (ev.type === "rate_limit_event") recordClaudeRate(ev.rate_limit_info); } catch { /* không phải JSON */ }
      }
    });
    p.on("error", () => resolve()); p.on("close", () => resolve());
    p.stdin.end("Trả lời đúng một chữ: ok");
    setTimeout(() => p.kill(), 60_000);
  });
}
