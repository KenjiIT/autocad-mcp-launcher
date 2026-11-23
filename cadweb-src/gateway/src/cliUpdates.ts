import { execFile, spawn } from "node:child_process";
import { realpathSync } from "node:fs";
import { claudeBin } from "./claudeSetup.js";
import { CODEX_BIN } from "./codexmodels.js";

// Kiểm tra và cập nhật các CLI mà gateway dùng (Claude Code, Codex CLI), giống bảng "CLI updates" của Orca.
// Bản đang cài: `<bin> --version`. Bản mới nhất: `npm view <pkg> version`. Lệnh cập nhật chọn theo cách CLI đó được cài.

const WIN = process.platform === "win32";
type Method = "native" | "npm" | "standalone" | "unknown";
type Def = { id: string; name: string; pkg: string; bin: () => string };
const DEFS: Def[] = [
  { id: "claude", name: "Claude Code", pkg: "@anthropic-ai/claude-code", bin: claudeBin },
  { id: "codex", name: "Codex CLI", pkg: "@openai/codex", bin: () => CODEX_BIN },
];

export type CliInfo = {
  id: string; name: string; pkg: string;
  installed: string | null; latest: string | null; method: Method; path: string | null;
  updateAvailable: boolean; canUpdate: boolean; hint: string | null;
  updating: boolean; progress: string | null; error: string | null;
};

const exec = (cmd: string, args: string[], timeout = 15_000) =>
  new Promise<{ ok: boolean; out: string }>(res =>
    execFile(cmd, args, { timeout, windowsHide: true, shell: WIN && !/\.exe$/i.test(cmd) }, (e, out) => res({ ok: !e, out: String(out ?? "") })));

const semver = (s: string | null) => s?.match(/\d+\.\d+\.\d+(?:-[\w.]+)?/)?.[0] ?? null;
const newer = (a: string, b: string) => {   // a > b ?
  const p = (v: string) => v.split(/[.-]/).slice(0, 3).map(Number);
  const x = p(a), y = p(b);
  for (let i = 0; i < 3; i++) if (x[i] !== y[i]) return x[i] > y[i];
  return false;
};

/** Đường dẫn thật của lệnh (theo PATH nếu chỉ là tên lệnh), để đoán cách cài. */
async function locate(bin: string): Promise<string | null> {
  let p = bin;
  if (!/[\\/]/.test(bin)) {
    const r = await exec(WIN ? "where" : "which", [bin], 5000);
    p = r.ok ? r.out.split(/\r?\n/).map(s => s.trim()).filter(Boolean)[0] ?? "" : "";
    if (!p) return null;
  }
  try { return realpathSync(p); } catch { return p; }
}

function methodOf(id: string, path: string | null): Method {
  if (!path) return "unknown";
  const p = path.replace(/\\/g, "/").toLowerCase();
  if (p.includes("/node_modules/") || p.includes("/npm/")) return "npm";
  if (id === "claude" && p.includes("/.local/")) return "native";
  if (id === "codex" && (p.includes("/openai/codex/") || p.includes("/.codex/packages/standalone/"))) return "standalone";
  return "unknown";
}

/** Lệnh cập nhật đúng cách cài; null = không tự cập nhật được (kèm gợi ý). */
function updateCmd(d: Def, m: Method, bin: string): { cmd: string; args: string[] } | null {
  if (m === "npm") return { cmd: WIN ? "npm.cmd" : "npm", args: ["install", "-g", `${d.pkg}@latest`] };
  if ((m === "native" && d.id === "claude") || (m === "standalone" && d.id === "codex")) return { cmd: bin, args: ["update"] };
  return null;
}
const HINT: Record<Method, string> = {
  npm: "", native: "",
  standalone: "",
  unknown: "Không rõ CLI được cài bằng cách nào nên không tự cập nhật được.",
};

const latestCache = new Map<string, { at: number; v: string | null }>();
async function latestOf(pkg: string, force: boolean): Promise<string | null> {
  const c = latestCache.get(pkg);
  if (!force && c && Date.now() - c.at < 30 * 60_000) return c.v;
  const r = await exec(WIN ? "npm.cmd" : "npm", ["view", pkg, "version"], 20_000);
  const v = r.ok ? semver(r.out.trim()) : c?.v ?? null;
  latestCache.set(pkg, { at: Date.now(), v });
  return v;
}

const jobs = new Map<string, { running: boolean; progress: string | null; error: string | null }>();

async function infoOf(d: Def, force: boolean): Promise<CliInfo> {
  const bin = d.bin();
  const [ver, path, latest] = await Promise.all([exec(bin, ["--version"], 10_000), locate(bin), latestOf(d.pkg, force)]);
  const installed = ver.ok ? semver(ver.out) : null;
  const method = methodOf(d.id, installed ? path : null);
  const over = process.env[`CLI_LATEST_${d.id.toUpperCase()}`];   // chỉ để thử giao diện: giả bản mới nhất
  const lat = over || latest;
  const j = jobs.get(d.id);
  const canUpdate = !!installed && !!updateCmd(d, method, bin);
  return {
    id: d.id, name: d.name, pkg: d.pkg, installed, latest: lat, method, path,
    updateAvailable: !!installed && !!lat && newer(lat, installed),
    canUpdate, hint: installed && !canUpdate ? HINT[method] || null : null,
    updating: !!j?.running, progress: j?.progress ?? null, error: j?.error ?? null,
  };
}

export const cliList = (force = false) => Promise.all(DEFS.map(d => infoOf(d, force)));

/** Chạy lệnh cập nhật ở nền; tiến độ (dòng log cuối) và lỗi xem qua cliList(). */
export async function startCliUpdate(id: string): Promise<{ error?: string }> {
  const d = DEFS.find(x => x.id === id);
  if (!d) return { error: "Không có CLI này." };
  if (jobs.get(id)?.running) return {};
  const bin = d.bin();
  const path = await locate(bin);
  const u = updateCmd(d, methodOf(id, path), bin);
  if (!u) return { error: HINT[methodOf(id, path)] || "Không tự cập nhật được CLI này." };
  const job = { running: true, progress: "Đang bắt đầu…" as string | null, error: null as string | null };
  jobs.set(id, job);
  let log = "";
  const p = spawn(u.cmd, u.args, { windowsHide: true, stdio: ["ignore", "pipe", "pipe"], shell: WIN && /\.cmd$/i.test(u.cmd) });
  const keep = (b: Buffer) => {
    log = (log + b.toString("utf8")).slice(-4000);
    const last = log.replace(/\x1b\[[0-9;]*[A-Za-z]/g, "").split(/[\r\n]+/).map(s => s.trim()).filter(Boolean).pop();
    if (last) job.progress = last.slice(0, 160);
  };
  p.stdout.on("data", keep); p.stderr.on("data", keep);
  p.on("error", e => { job.running = false; job.error = `Không chạy được lệnh cập nhật: ${e.message}`; });
  p.on("close", code => {
    job.running = false;
    if (code !== 0) { job.error = `Cập nhật không thành công (mã ${code}). ${log.trim().split(/\r?\n/).slice(-2).join(" ")}`.trim(); console.error(`cli update ${id}:`, log); }
    else { job.progress = null; job.error = null; }
  });
  return {};
}
