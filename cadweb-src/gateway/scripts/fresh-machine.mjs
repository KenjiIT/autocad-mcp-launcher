// Mô phỏng MÁY MỚI để thử luồng cài + đăng nhập Claude CLI của CAD Studio mà không phá máy đang dùng:
//  - USERPROFILE/HOME/APPDATA/LOCALAPPDATA trỏ vào thư mục tạm, CLAUDE_CONFIG_DIR riêng;
//  - PATH đã lọc bỏ mọi thư mục có claude/node/npm/git/bash; ProgramFiles trỏ vào thư mục trống (không thấy Git Bash);
//  - cài THẬT bằng bộ cài chính thức (cần mạng), mở cửa sổ đăng nhập thật rồi chụp ảnh cửa sổ đó, KHÔNG đăng nhập;
//  - lưu và khôi phục PATH người dùng trong registry (bộ cài có thể thêm ~/.local/bin của thư mục tạm vào đó);
//  - cuối cùng tắt cửa sổ đăng nhập và xoá thư mục tạm.
// Chạy: node scripts/fresh-machine.mjs [thư mục ảnh]   (từ cad-web-local/gateway)
import { execFileSync, spawn, spawnSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, delimiter } from "node:path";
import { fileURLToPath } from "node:url";

const OUT = process.argv[2] ?? ".";
const STARTED = new Date();
const HERE = fileURLToPath(new URL(".", import.meta.url));
const TMP = mkdtempSync(join(tmpdir(), "cad-fresh-"));
const HOME = join(TMP, "Nguyễn Văn A");   // tên tài khoản có dấu + khoảng trắng như nhiều máy thật
const lines = [];
const say = (...a) => { const s = a.join(" "); lines.push(s); console.log(s); };

const regPath = () => { try { return execFileSync("powershell.exe", ["-NoProfile", "-Command", "[Environment]::GetEnvironmentVariable('Path','User')"], { encoding: "utf8" }).trim(); } catch { return null; } };
const userPathBefore = regPath();

for (const d of [HOME, join(HOME, "AppData", "Roaming"), join(HOME, "AppData", "Local"), join(TMP, "pf"), join(TMP, "pf86")]) mkdirSync(d, { recursive: true });
const BAD = ["claude.exe", "claude.cmd", "claude", "node.exe", "npm.cmd", "git.exe", "bash.exe"];
const keepDir = d => { try { return !readdirSync(d).some(f => BAD.includes(f.toLowerCase())); } catch { return false; } };
const path = (process.env.PATH ?? "").split(delimiter).filter(d => d && keepDir(d) && !/\\(git|nodejs|npm)\\?/i.test(d) && !/\.local\\bin/i.test(d));
const env = { ...process.env, USERPROFILE: HOME, HOME, APPDATA: join(HOME, "AppData", "Roaming"), LOCALAPPDATA: join(HOME, "AppData", "Local"),
  CLAUDE_CONFIG_DIR: join(HOME, ".claude-cfg"), PATH: path.join(delimiter), ProgramFiles: join(TMP, "pf"), "ProgramFiles(x86)": join(TMP, "pf86"),
  ProgramW6432: join(TMP, "pf") };
for (const k of Object.keys(env)) if (/^(CLAUDE_BIN|CLAUDE_CODE_|CLAUDECODE|ORCA_)/.test(k) || k === "Path") delete env[k];
say(`# Mô phỏng máy mới — ${new Date().toISOString()}`);
say(`HOME tạm: ${HOME}`);
say(`PATH còn ${path.length} thư mục (đã bỏ claude/node/npm/git/bash)`);

// Chạy bước con bằng node + tsx (đường dẫn tuyệt đối vì PATH đã bỏ node)
const tsx = join(HERE, "..", "..", "node_modules", "tsx", "dist", "cli.mjs");
const child = spawn(process.execPath, [tsx, join(HERE, "fresh-machine-child.ts")], { env, cwd: join(HERE, ".."), stdio: ["ignore", "pipe", "pipe"] });
let buf = "", loginShot = false;
child.stderr.on("data", d => say("  [stderr]", String(d).trim().slice(0, 300)));
child.stdout.on("data", d => {
  buf += d;
  let i;
  while ((i = buf.indexOf("\n")) >= 0) {
    const line = buf.slice(0, i); buf = buf.slice(i + 1);
    try {
      const j = JSON.parse(line);
      say(`\n## ${j.step}\n${JSON.stringify(j.data, null, 2).slice(0, 2500)}`);
      if (j.step === "5-mo-dang-nhap" && !loginShot) { loginShot = true; setTimeout(shootLogin, 6000); }
    } catch { say("  ", line); }
  }
});

function loginProcs() {
  const r = spawnSync("powershell.exe", ["-NoProfile", "-Command",
    `Get-CimInstance Win32_Process | ? { $_.CommandLine -like '*${TMP.replace(/'/g, "''")}*' -and $_.CommandLine -like '*auth login*' } | % { $_.ProcessId }`], { encoding: "utf8" });
  return (r.stdout || "").split(/\s+/).filter(Boolean).map(Number);
}
function shootLogin() {
  const pids = loginProcs();
  say(`\n## anh-cua-so-dang-nhap\nTiến trình đăng nhập: ${pids.join(", ") || "KHÔNG THẤY"}`);
  const info = spawnSync("powershell.exe", ["-NoProfile", "-Command",
    "Get-CimInstance Win32_Process | ? { $_.CommandLine -like '*auth login*' -and $_.Name -ne 'powershell.exe' } | % { $p = Get-Process -Id $_.ProcessId -ea 0; \"$($_.ProcessId) $($_.Name) parent=$($_.ParentProcessId) hwnd=$($p.MainWindowHandle) title=$($p.MainWindowTitle)\" }"], { encoding: "utf8" });
  say((info.stdout || "").trim());
  const r = spawnSync("powershell.exe", ["-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", `
    Add-Type @"
using System; using System.Runtime.InteropServices;
public static class FW { [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr dc, uint f);
 [DllImport("dwmapi.dll")] public static extern int DwmGetWindowAttribute(IntPtr h, int a, out R r, int s);
 [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h); [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
 public struct R { public int L,T,Ri,B; } }
"@
    Add-Type -AssemblyName System.Drawing
    $p = Get-Process -Id ${pids.join(",") || "0"} -ErrorAction SilentlyContinue | ? { $_.MainWindowHandle -ne 0 } | select -First 1
    if (-not $p) { 'NO_WINDOW'; exit }
    $h = $p.MainWindowHandle; [FW]::SetForegroundWindow($h) | Out-Null; Start-Sleep -m 800
    $r = New-Object FW+R; [FW]::DwmGetWindowAttribute($h, 9, [ref]$r, 16) | Out-Null
    $b = New-Object Drawing.Bitmap ($r.Ri-$r.L), ($r.B-$r.T); $g=[Drawing.Graphics]::FromImage($b); $dc=$g.GetHdc(); [FW]::PrintWindow($h, $dc, 2) | Out-Null; $g.ReleaseHdc($dc)
    $b.Save('${join(OUT, "claude-may-moi-cua-so-dang-nhap.png").replace(/'/g, "''")}'); "VISIBLE=$([FW]::IsWindowVisible($h)) TITLE=$($p.MainWindowTitle)"`], { encoding: "utf8" });
  say((r.stdout || r.stderr || "").trim());
}

child.on("exit", code => {
  say(`\n## ket-thuc (mã ${code})`);
  for (const pid of loginProcs()) spawnSync("taskkill", ["/F", "/T", "/PID", String(pid)]);
  // Trình duyệt mà `claude auth login` mở (hồ sơ Edge nằm trong thư mục tạm): tắt để còn xoá được thư mục tạm
  spawnSync("powershell.exe", ["-NoProfile", "-Command",
    `Get-CimInstance Win32_Process | ? { $_.CommandLine -like '*oauth/authorize*' -and $_.CreationDate -gt [datetime]'${STARTED.toISOString()}' } | % { taskkill /F /T /PID $_.ProcessId | Out-Null }`]);
  const after = regPath();
  if (userPathBefore !== null && after !== userPathBefore) {
    spawnSync("powershell.exe", ["-NoProfile", "-Command", `[Environment]::SetEnvironmentVariable('Path', '${userPathBefore.replace(/'/g, "''")}', 'User')`]);
    say(`PATH người dùng trong registry đã bị bộ cài sửa -> đã khôi phục như cũ.`);
  } else say("PATH người dùng trong registry không đổi.");
  writeFileSync(join(OUT, "claude-may-moi-log.md"), lines.join("\n"), "utf8");
  const clean = (n) => {
    try { rmSync(TMP, { recursive: true, force: true }); } catch (e) { if (n > 0) return setTimeout(() => clean(n - 1), 3000); console.error("chưa xoá được thư mục tạm:", e.message); }
    console.log(existsSync(TMP) ? `CÒN thư mục tạm: ${TMP}` : "Đã xoá thư mục tạm.");
  };
  setTimeout(() => clean(5), 2000);
});
