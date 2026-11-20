import { execFile, spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

const WIN = process.platform === "win32";
// Bộ cài chính thức đặt claude vào ~/.local/bin, thư mục này thường chưa có trong PATH của gateway đang chạy.
const NATIVE = join(homedir(), ".local", "bin", WIN ? "claude.exe" : "claude");

export const claudeBin = () => process.env.CLAUDE_BIN || (existsSync(NATIVE) ? NATIVE : "claude");

const run = (args: string[], timeout = 10_000) =>
  new Promise<{ ok: boolean; out: string }>(res =>
    execFile(claudeBin(), args, { timeout, windowsHide: true }, (e, out) => res({ ok: !e, out: String(out ?? "") })));

let install: { running: boolean; error?: string; log: string } = { running: false, log: "" };

export type ClaudeStatus = { installed: boolean; version: string | null; loggedIn: boolean; email: string | null; installing: boolean; installError: string | null };

export async function claudeStatus(): Promise<ClaudeStatus> {
  const base = { installing: install.running, installError: install.error ?? null };
  const v = await run(["--version"]);
  if (!v.ok) return { ...base, installed: false, version: null, loggedIn: false, email: null };
  const s = await run(["auth", "status"]);
  let loggedIn = false, email: string | null = null;
  try { const j = JSON.parse(s.out); loggedIn = j.loggedIn === true; email = typeof j.email === "string" ? j.email : null; } catch { /* bản CLI cũ không có JSON */ }
  return { ...base, installed: true, version: v.out.trim(), loggedIn, email };
}

/** Tải và chạy bộ cài chính thức của Claude Code (không cần quyền quản trị). Chạy nền; xem tiến độ qua claudeStatus(). */
export function startInstall(): { error?: string } {
  if (install.running) return {};
  const [cmd, args] = WIN
    ? ["powershell.exe", ["-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "irm https://claude.ai/install.ps1 | iex"]]
    : ["bash", ["-c", "curl -fsSL https://claude.ai/install.sh | bash"]];
  install = { running: true, log: "" };
  const p = spawn(cmd, args as string[], { windowsHide: true, stdio: ["ignore", "pipe", "pipe"] });
  const keep = (d: Buffer) => { install.log = (install.log + d.toString("utf8")).slice(-4000); };
  p.stdout.on("data", keep); p.stderr.on("data", keep);
  p.on("error", e => { install = { running: false, log: install.log, error: `Không chạy được bộ cài: ${e.message}` }; });
  p.on("close", code => {
    const ok = code === 0 && (existsSync(NATIVE) || !!process.env.CLAUDE_BIN);
    install = { running: false, log: install.log, ...(ok ? {} : { error: `Cài không thành công (mã ${code}). ${install.log.trim().split(/\r?\n/).slice(-3).join(" ")}`.trim() }) };
    if (!ok) console.error("claude install:", install.log);
  });
  return {};
}

/** Mở một cửa sổ riêng trên máy này chạy `claude auth login`; người dùng làm tiếp trên trình duyệt. */
export function startLogin(): { error?: string } {
  if (!WIN) return { error: "Mở terminal trên máy này và chạy: claude auth login" };
  const bin = claudeBin().replace(/'/g, "''");
  const p = spawn("powershell.exe", ["-NoProfile", "-Command", `Start-Process -FilePath '${bin}' -ArgumentList 'auth','login'`],
    { windowsHide: true, stdio: "ignore", detached: true });
  p.on("error", e => console.error("claude login:", e.message));
  p.unref();
  return {};
}
