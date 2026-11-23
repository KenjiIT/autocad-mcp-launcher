import { execFile, spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { homedir } from "node:os";
import { delimiter, dirname, join } from "node:path";

const WIN = process.platform === "win32";
// Bộ cài chính thức đặt claude vào ~/.local/bin. Thư mục này thường CHƯA có trong PATH của gateway đang chạy
// (PATH của tiến trình chỉ cập nhật khi mở lại), nên luôn tìm thẳng ở đó, tính lại mỗi lần (USERPROFILE có thể đổi khi test).
const native = () => join(homedir(), ".local", "bin", WIN ? "claude.exe" : "claude");

/** Tìm một lệnh trên PATH hiện tại của tiến trình (không gọi shell). */
export function which(name: string, env: NodeJS.ProcessEnv = process.env): string | null {
  const exts = WIN ? (env.PATHEXT ?? ".EXE;.CMD;.BAT").split(";").map(e => e.toLowerCase()) : [""];
  for (const dir of (env.PATH ?? env.Path ?? "").split(delimiter)) {
    if (!dir) continue;
    for (const ext of exts) {
      const p = join(dir, WIN && !name.toLowerCase().endsWith(ext) ? name + ext : name);
      if (existsSync(p)) return p;
    }
  }
  return null;
}

export const claudeBin = () => process.env.CLAUDE_BIN || (existsSync(native()) ? native() : which("claude") ?? "claude");

/**
 * Git Bash (đi kèm Git for Windows): Claude Code dùng để chạy lệnh bash nếu có; không có thì dùng PowerShell (đã thử).
 * Trả đường dẫn bash.exe tìm được (CLAUDE_CODE_GIT_BASH_PATH, chỗ cài thường gặp, hoặc cạnh git.exe trên PATH), hoặc null.
 */
export function gitBash(env: NodeJS.ProcessEnv = process.env): string | null {
  if (!WIN) return "/bin/bash";
  const set = env.CLAUDE_CODE_GIT_BASH_PATH;
  if (set && existsSync(set)) return set;
  const roots = [env.ProgramFiles, env["ProgramFiles(x86)"], env.LOCALAPPDATA && join(env.LOCALAPPDATA, "Programs")].filter(Boolean) as string[];
  for (const r of roots) {
    const p = join(r, "Git", "bin", "bash.exe");
    if (existsSync(p)) return p;
  }
  const git = which("git", env);
  if (git) {
    const p = join(dirname(dirname(git)), "bin", "bash.exe");   // ...\Git\cmd\git.exe -> ...\Git\bin\bash.exe
    if (existsSync(p)) return p;
  }
  return null;
}

const run = (args: string[], timeout = 10_000) =>
  new Promise<{ ok: boolean; out: string }>(res =>
    execFile(claudeBin(), args, { timeout, windowsHide: true }, (e, out) => res({ ok: !e, out: String(out ?? "") })));

export type InstallProblem = "network" | "policy" | "arch" | "npm" | "unknown";
let install: { running: boolean; error?: string; problem?: InstallProblem; log: string; via?: string } = { running: false, log: "" };

/** Lỗi cài dễ hiểu từ log của bộ cài: bị chặn mạng/proxy, ExecutionPolicy, máy 32-bit… (tách ra để kiểm thử). */
export function classifyInstallError(log: string): { problem: InstallProblem; message: string } {
  const l = log.toLowerCase();
  if (/(unable to connect|could not resolve|remote name could not be resolved|name or service not known|timed out|timeout|proxy|403|407|ssl|tls|connection.*(closed|reset)|enotfound|econnrefused|econnreset|etimedout|unable to (download|fetch)|failed to (download|fetch))/.test(l))
    return { problem: "network", message: "Bị chặn khi tải bộ cài từ claude.ai / storage.googleapis.com. Kiểm tra mạng, proxy hoặc tường lửa công ty rồi thử lại." };
  if (/(execution ?policy|running scripts is disabled|cannot be loaded because|psecurityexception)/.test(l))
    return { problem: "policy", message: "PowerShell đang chặn chạy script cài (ExecutionPolicy). Thử lại; nếu vẫn bị, cài qua npm hoặc nhờ quản trị máy cho phép." };
  if (/(32-bit|is64bitprocess|not supported on this (platform|architecture))/.test(l))
    return { problem: "arch", message: "Claude Code cần Windows 64-bit." };
  return { problem: "unknown", message: "Cài không thành công. " + log.trim().split(/\r?\n/).filter(Boolean).slice(-3).join(" ").slice(0, 300) };
}

export type ClaudeStatus = {
  installed: boolean; version: string | null; loggedIn: boolean; email: string | null; installing: boolean; installError: string | null;
  installProblem: InstallProblem | null; path: string | null; gitBash: string | null; needsGit: boolean;
};

export async function claudeStatus(): Promise<ClaudeStatus> {
  const bash = gitBash();
  const base = { installing: install.running, installError: install.error ?? null, installProblem: install.problem ?? null, gitBash: bash, needsGit: WIN && !bash };
  const v = await run(["--version"]);
  if (!v.ok) return { ...base, installed: false, version: null, loggedIn: false, email: null, path: null };
  const s = await run(["auth", "status"]);
  let loggedIn = false, email: string | null = null;
  try { const j = JSON.parse(s.out); loggedIn = j.loggedIn === true; email = typeof j.email === "string" ? j.email : null; } catch { /* bản CLI cũ không có JSON */ }
  return { ...base, installed: true, version: v.out.trim(), loggedIn, email, path: claudeBin() };
}

/** Lệnh cài: bộ cài chính thức (không cần Node, không cần quyền quản trị) hoặc npm (dự phòng). Tách ra để kiểm thử. */
export function installCommand(via: "script" | "npm", win = WIN): [string, string[]] {
  if (via === "npm") return win ? ["cmd.exe", ["/d", "/s", "/c", "npm i -g @anthropic-ai/claude-code"]] : ["npm", ["i", "-g", "@anthropic-ai/claude-code"]];
  return win
    ? ["powershell.exe", ["-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
      "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; irm https://claude.ai/install.ps1 | iex"]]
    : ["bash", ["-c", "curl -fsSL https://claude.ai/install.sh | bash"]];
}

/**
 * Tải và cài Claude Code ở nền; xem tiến độ qua claudeStatus(). Bộ cài chính thức lỗi (không phải do mạng) mà máy có npm
 * thì tự thử cài qua npm. Sau khi cài, claudeBin() tìm thẳng ~/.local/bin nên không cần khởi động lại gateway.
 */
export function startInstall(opts: { via?: "script" | "npm"; onDone?: () => void } = {}): { error?: string } {
  if (install.running) return {};
  const via = opts.via ?? "script";
  if (via === "npm" && !which("npm")) return { error: "Máy chưa có Node.js/npm nên không cài qua npm được. Dùng bộ cài chính thức." };
  const [cmd, args] = installCommand(via);
  install = { running: true, log: "", via };
  const p = spawn(cmd, args, { windowsHide: true, stdio: ["ignore", "pipe", "pipe"] });
  const keep = (d: Buffer) => { install.log = (install.log + d.toString("utf8")).slice(-8000); };
  p.stdout.on("data", keep); p.stderr.on("data", keep);
  p.on("error", e => { install = { running: false, log: install.log, via, ...classifyInstallError(e.message), error: `Không chạy được bộ cài (${cmd}): ${e.message}` }; opts.onDone?.(); });
  p.on("close", code => {
    const ok = code === 0 && (existsSync(native()) || !!which("claude") || !!process.env.CLAUDE_BIN);
    if (ok) { install = { running: false, log: install.log, via }; opts.onDone?.(); return; }
    const c = classifyInstallError(install.log || `mã thoát ${code}`);
    console.error(`claude install (${via}) lỗi, mã ${code}:`, install.log);
    if (via === "script" && c.problem !== "network" && which("npm")) {   // dự phòng: thử npm
      install = { running: false, log: install.log };
      startInstall({ via: "npm", onDone: opts.onDone });
      return;
    }
    install = { running: false, log: install.log, via, problem: c.problem, error: c.message };
    opts.onDone?.();
  });
  return {};
}

/**
 * Lệnh mở cửa sổ console THẤY ĐƯỢC chạy `claude auth login` (Claude tự mở trình duyệt; không mở được thì in đường link
 * trong cửa sổ). Dùng `cmd /k` (cửa sổ giữ lại sau khi xong, thấy được lỗi): thử thật trên môi trường máy mới, cách
 * bọc bằng một powershell -NoExit thứ hai không hiện cửa sổ nào. Đường dẫn có dấu/khoảng trắng được bọc nháy kép.
 */
export function loginCommand(bin: string): [string, string[]] {
  // Không qua PowerShell: trên máy mới (hồ sơ người dùng trống) powershell khởi động rất chậm, cửa sổ không kịp hiện.
  // `start` của cmd luôn mở cửa sổ console mới thấy được; truyền nguyên văn (windowsVerbatimArguments) để giữ nháy kép.
  return ["cmd.exe", [`/d /s /c start "Claude - dang nhap" cmd /k ""${bin}" auth login"`]];
}

/** Mở một cửa sổ riêng (thấy được) chạy `claude auth login`; người dùng làm tiếp trên trình duyệt. */
export function startLogin(): { error?: string } {
  if (!WIN) return { error: "Mở terminal trên máy này và chạy: claude auth login" };
  const bin = claudeBin();
  if (bin === "claude" && !which("claude")) return { error: "Chưa cài Claude CLI. Bấm Cài đặt trước." };
  const [cmd, args] = loginCommand(bin);
  const p = spawn(cmd, args, { windowsHide: true, stdio: "ignore", detached: true, windowsVerbatimArguments: true });
  p.on("error", e => console.error("claude login:", e.message));
  p.unref();
  return {};
}

/** Mở trang tải Git for Windows (Claude Code trên Windows cần Git Bash); có winget thì cài thẳng. */
export function startGitInstall(): { error?: string; opened?: string } {
  if (!WIN) return { error: "Chỉ cần trên Windows." };
  if (which("winget")) {
    const p = spawn("powershell.exe", ["-NoProfile", "-Command",
      "Start-Process -WindowStyle Normal powershell.exe -ArgumentList '-NoProfile','-NoExit','-Command','winget install --id Git.Git -e --accept-package-agreements --accept-source-agreements'"],
      { windowsHide: true, stdio: "ignore", detached: true });
    p.unref();
    return { opened: "winget" };
  }
  spawn("cmd.exe", ["/c", "start", "", "https://git-scm.com/download/win"], { windowsHide: true, stdio: "ignore", detached: true }).unref();
  return { opened: "browser" };
}

export type Check = { id: string; label: string; ok: boolean; detail: string; fix?: "install" | "login" | "git" | "guide" };

/** "Kiểm tra máy": các điều kiện để Claude CLI chạy được trên máy này. */
export async function machineCheck(fetchImpl: typeof fetch = fetch): Promise<Check[]> {
  const st = await claudeStatus();
  const checks: Check[] = [];
  const net = await fetchImpl("https://claude.ai/install.ps1", { method: "HEAD", signal: AbortSignal.timeout(6000) })
    .then(r => ({ ok: r.ok, detail: `claude.ai trả ${r.status}` }))
    .catch((e: any) => ({ ok: false, detail: `Không tới được claude.ai (${e?.cause?.code ?? e?.name ?? e}). Kiểm tra mạng/proxy.` }));
  checks.push({ id: "network", label: "Mạng tới claude.ai", ok: net.ok, detail: net.detail, fix: net.ok ? undefined : "guide" });
  checks.push({ id: "claude", label: "Claude CLI", ok: st.installed, detail: st.installed ? `${st.version} · ${st.path}` : (st.installError ?? "Chưa cài trên máy này."), fix: st.installed ? undefined : "install" });
  // Đã thử: Claude Code bản hiện tại vẫn chat được khi không có Git Bash (dùng PowerShell), nên chỉ là khuyến nghị.
  if (WIN) checks.push({ id: "git", label: "Git for Windows (khuyến nghị)", ok: true, detail: st.gitBash
    ? `Git Bash: ${st.gitBash}` : "Chưa có Git Bash. Không bắt buộc (agent dùng PowerShell); cài Git nếu muốn agent chạy lệnh bash/git.", fix: st.gitBash ? undefined : "git" });
  const localBin = dirname(native());
  const inPath = (process.env.PATH ?? "").toLowerCase().split(delimiter).includes(localBin.toLowerCase());
  checks.push({ id: "path", label: "PATH", ok: true, detail: inPath ? `${localBin} có trong PATH.` : `${localBin} chưa có trong PATH của gateway; không sao: CAD Studio tìm thẳng ở đó.` });
  checks.push({ id: "node", label: "Node.js / npm (chỉ để cài dự phòng)", ok: true, detail: which("npm") ? `npm: ${which("npm")}` : "Không có npm; dùng bộ cài chính thức (không cần Node)." });
  checks.push({ id: "login", label: "Đăng nhập Claude", ok: st.loggedIn, detail: st.loggedIn ? `Đã đăng nhập${st.email ? ": " + st.email : ""}` : "Chưa đăng nhập.", fix: st.loggedIn || !st.installed ? undefined : "login" });
  const cfg = process.env.CLAUDE_CONFIG_DIR;
  checks.push({ id: "profile", label: "Hồ sơ Claude", ok: true, detail: cfg ? `CLAUDE_CONFIG_DIR = ${cfg}` : `Mặc định (${join(homedir(), ".claude")})` });
  const home = homedir();
  checks.push({ id: "home", label: "Thư mục tài khoản Windows", ok: true, detail: /[^\x20-\x7e]/.test(home) || home.includes(" ") ? `${home} (có dấu/khoảng trắng: đã hỗ trợ)` : home });
  return checks;
}
