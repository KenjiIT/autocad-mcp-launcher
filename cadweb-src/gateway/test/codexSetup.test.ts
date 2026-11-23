import { test } from "node:test";
import assert from "node:assert/strict";
import { codexInstallCommand, codexLoginCommand, codexSetupStatus, startCodexInstall } from "../src/codexSetup.js";

test("lệnh cài Codex là npm i -g @openai/codex (Windows qua cmd)", () => {
  assert.deepEqual(codexInstallCommand(false), ["npm", ["i", "-g", "@openai/codex"]]);
  const [cmd, args] = codexInstallCommand(true);
  assert.equal(cmd, "cmd.exe"); assert.match(args.join(" "), /npm i -g @openai\/codex/);
});

test("đăng nhập Codex mở cửa sổ PowerShell chạy codex login; ngoài Windows thì hướng dẫn tự chạy", () => {
  const c = codexLoginCommand("C:\\bin\\codex.cmd", true)!;
  assert.equal(c[0], "cmd.exe");
  assert.match(c[1][0], /start "Codex - dang nhap" cmd \/k ""C:.bin.codex\.cmd" login"/);
  assert.equal(codexLoginCommand("codex", false), null);
});

test("trạng thái cài: đang cài rồi báo lỗi khi lệnh cài thất bại", async () => {
  const fail: [string, string[]] = [process.execPath, ["-e", "console.error('npm ERR! boom'); process.exit(3)"]];
  startCodexInstall(fail);
  assert.equal((await codexSetupStatus()).installing, true);
  for (let i = 0; i < 100 && (await codexSetupStatus()).installing; i++) await new Promise(r => setTimeout(r, 50));
  const s = await codexSetupStatus();
  assert.equal(s.installing, false);
  assert.match(s.installError ?? "", /mã 3[\s\S]*boom/);
});
