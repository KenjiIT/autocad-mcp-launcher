import { spawn } from "node:child_process";
import { codexStatus } from "./codex.js";
import { CODEX_BIN } from "./codexmodels.js";

// Cài và đăng nhập Codex CLI ngay trên máy này, giống claudeSetup.ts cho Claude.
const WIN = process.platform === "win32";

let install: { running: boolean; error?: string; log: string } = { running: false, log: "" };

export type CodexSetupStatus = { installed: boolean; version: string | null; loggedIn: boolean; installing: boolean; installError: string | null };

/** Lệnh cài Codex: npm i -g @openai/codex (Windows phải gọi npm.cmd qua cmd). Tách riêng để kiểm thử. */
export function codexInstallCommand(win = WIN): [string, string[]] {
  return win ? ["cmd.exe", ["/d", "/s", "/c", "npm i -g @openai/codex"]] : ["npm", ["i", "-g", "@openai/codex"]];
}

/** Lệnh mở cửa sổ riêng chạy `codex login` (Codex tự mở trình duyệt). Không phải Windows thì null: tự chạy trong terminal. */
export function codexLoginCommand(bin = CODEX_BIN, win = WIN): [string, string[]] | null {
  if (!win) return null;
  // Như Claude: mở thẳng cửa sổ cmd (thấy được, giữ lại để xem lỗi); không lồng PowerShell (chậm/không hiện trên máy mới).
  return ["cmd.exe", [`/d /s /c start "Codex - dang nhap" cmd /k ""${bin}" login"`]];
}

export async function codexSetupStatus(): Promise<CodexSetupStatus> {
  const base = { installing: install.running, installError: install.error ?? null };   // chụp trước khi hỏi codex (có thể chậm)
  if (base.installing) return { installed: false, version: null, loggedIn: false, ...base };   // đang cài thì chưa hỏi codex
  return { ...(await codexStatus()), ...base };
}

/** Chạy `npm i -g @openai/codex` ở nền; xem tiến độ qua codexSetupStatus(). */
export function startCodexInstall(cmd: [string, string[]] = codexInstallCommand()): { error?: string } {
  if (install.running) return {};
  install = { running: true, log: "" };
  const p = spawn(cmd[0], cmd[1], { windowsHide: true, stdio: ["ignore", "pipe", "pipe"] });
  const keep = (d: Buffer) => { install.log = (install.log + d.toString("utf8")).slice(-4000); };
  p.stdout.on("data", keep); p.stderr.on("data", keep);
  p.on("error", e => { install = { running: false, log: install.log, error: `Không chạy được npm: ${e.message}. Cần cài Node.js trước.` }; });
  p.on("close", code => {
    if (!install.running) return;
    install = { running: false, log: install.log, ...(code === 0 ? {} : { error: `Cài Codex không thành công (mã ${code}). ${install.log.trim().split(/\r?\n/).slice(-3).join(" ")}`.trim() }) };
  });
  return {};
}

export function startCodexLogin(): { error?: string } {
  const c = codexLoginCommand();
  if (!c) return { error: "Mở terminal trên máy này và chạy: codex login" };
  const p = spawn(c[0], c[1], { windowsHide: true, stdio: "ignore", detached: true, windowsVerbatimArguments: true });
  p.on("error", e => console.error("codex login:", e.message));
  p.unref();
  return {};
}
