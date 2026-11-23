// Cài / đăng nhập Claude CLI trên máy mới (claudeSetup.ts): phân loại lỗi cài, lệnh cài/đăng nhập, tìm Git Bash, Kiểm tra máy.
import { test, after } from "node:test";
import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { classifyInstallError, gitBash, installCommand, loginCommand, machineCheck, which } from "../src/claudeSetup.js";

const TMP = mkdtempSync(join(tmpdir(), "cad-claude-setup-"));
after(() => rmSync(TMP, { recursive: true, force: true }));

test("lỗi cài được phân loại thành nguyên nhân dễ hiểu", () => {
  assert.equal(classifyInstallError("Invoke-WebRequest : Unable to connect to the remote server").problem, "network");
  assert.equal(classifyInstallError("The remote name could not be resolved: 'claude.ai'").problem, "network");
  assert.equal(classifyInstallError("(407) Proxy Authentication Required").problem, "network");
  assert.equal(classifyInstallError("File install.ps1 cannot be loaded because running scripts is disabled on this system").problem, "policy");
  assert.equal(classifyInstallError("Claude Code does not support 32-bit Windows").problem, "arch");
  const u = classifyInstallError("lạ 1\nlạ 2\nlỗi cuối");
  assert.equal(u.problem, "unknown"); assert.match(u.message, /lỗi cuối/);
  assert.match(classifyInstallError("timed out").message, /mạng, proxy/);
});

test("lệnh cài: bộ cài chính thức (TLS 1.2, bỏ qua ExecutionPolicy) và dự phòng npm", () => {
  const [c, a] = installCommand("script", true);
  assert.equal(c, "powershell.exe");
  assert.ok(a.includes("Bypass") && a.join(" ").includes("Tls12") && a.join(" ").includes("claude.ai/install.ps1"));
  assert.deepEqual(installCommand("npm", false), ["npm", ["i", "-g", "@anthropic-ai/claude-code"]]);
  assert.match(installCommand("npm", true)[1].join(" "), /npm i -g @anthropic-ai\/claude-code/);
});

test("lệnh đăng nhập mở cửa sổ cmd thấy được, đường dẫn có dấu/khoảng trắng được bọc nháy", () => {
  const bin = "C:\\Users\\Nguyễn Văn A\\.local\\bin\\claude.exe";
  const [c, a] = loginCommand(bin);
  assert.equal(c, "cmd.exe");
  assert.equal(a.length, 1);
  assert.equal(a[0], `/d /s /c start "Claude - dang nhap" cmd /k ""${bin}" auth login"`);
});

test("tìm lệnh trên PATH và Git Bash ở chỗ cài thường gặp / cạnh git.exe", () => {
  const bin = join(TMP, "bin"); mkdirSync(bin, { recursive: true });
  writeFileSync(join(bin, "tool.exe"), "");
  const env = { PATH: bin, PATHEXT: ".EXE" };
  if (process.platform === "win32") {
    assert.equal(which("tool", env), join(bin, "tool.exe"));
    assert.equal(which("khongco", env), null);
    const pf = join(TMP, "pf"); mkdirSync(join(pf, "Git", "bin"), { recursive: true }); writeFileSync(join(pf, "Git", "bin", "bash.exe"), "");
    assert.equal(gitBash({ ProgramFiles: pf, PATH: "" }), join(pf, "Git", "bin", "bash.exe"));
    const alt = join(TMP, "alt"); mkdirSync(join(alt, "Git", "cmd"), { recursive: true }); mkdirSync(join(alt, "Git", "bin"), { recursive: true });
    writeFileSync(join(alt, "Git", "cmd", "git.exe"), ""); writeFileSync(join(alt, "Git", "bin", "bash.exe"), "");
    assert.equal(gitBash({ PATH: join(alt, "Git", "cmd"), PATHEXT: ".EXE" }), join(alt, "Git", "bin", "bash.exe"));
    assert.equal(gitBash({ PATH: "", ProgramFiles: join(TMP, "trong") }), null);
  }
});

test("Kiểm tra máy: mạng bị chặn thì báo rõ và có nút hướng dẫn; luôn có mục Claude CLI, đăng nhập, hồ sơ", async () => {
  const blocked = (async () => { throw Object.assign(new Error("fetch failed"), { cause: { code: "ENOTFOUND" } }); }) as unknown as typeof fetch;
  const checks = await machineCheck(blocked);
  const net = checks.find(c => c.id === "network")!;
  assert.equal(net.ok, false); assert.equal(net.fix, "guide"); assert.match(net.detail, /ENOTFOUND/);
  for (const id of ["claude", "login", "profile", "path", "node", "home"]) assert.ok(checks.some(c => c.id === id), id);
  const ok = await machineCheck((async () => new Response(null, { status: 200 })) as unknown as typeof fetch);
  assert.equal(ok.find(c => c.id === "network")!.ok, true);
});
