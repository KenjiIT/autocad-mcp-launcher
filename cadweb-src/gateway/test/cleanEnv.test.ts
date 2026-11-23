import { test } from "node:test";
import assert from "node:assert/strict";
import { cleanEnv } from "../src/cleanEnv.js";

const ORCA = { PATH: "x", CLAUDECODE: "1", CLAUDE_CODE_ENTRYPOINT: "orca", CLAUDE_CODE_MESSAGING_SOCKET: "pipe", CLAUDE_PID: "1", CLAUDE_EFFORT: "low",
  ORCA_AGENT_SESSION_ID: "s", ORCA_AGENT_SESSION_SPAWN_TOKEN: "t", CLAUDE_CONFIG_DIR: "C:\\Users\\u\\orca\\home", ANTHROPIC_API_KEY: "k", CLAUDE_BIN: "c" };

test("bỏ biến phiên Orca/Claude Code, giữ biến của CAD Studio; mặc định giữ hồ sơ Claude", () => {
  const { env, dropped } = cleanEnv(ORCA);
  assert.deepEqual(Object.keys(env).sort(), ["ANTHROPIC_API_KEY", "CLAUDE_BIN", "CLAUDE_CONFIG_DIR", "PATH"]);
  assert.ok(dropped.includes("CLAUDECODE") && dropped.includes("ORCA_AGENT_SESSION_SPAWN_TOKEN") && dropped.includes("CLAUDE_CODE_MESSAGING_SOCKET"));
  assert.equal(ORCA.CLAUDECODE, "1", "không sửa env gốc");
});

test("CAD_CLAUDE_CONFIG_DIR=default dùng ~/.claude; đặt đường dẫn thì dùng đường dẫn đó", () => {
  assert.equal(cleanEnv({ ...ORCA, CAD_CLAUDE_CONFIG_DIR: "default" }).env.CLAUDE_CONFIG_DIR, undefined);
  assert.equal(cleanEnv({ ...ORCA, CAD_CLAUDE_CONFIG_DIR: " D:\\cfg " }).env.CLAUDE_CONFIG_DIR, "D:\\cfg");
  assert.equal(cleanEnv({ PATH: "x", CAD_CLAUDE_CONFIG_DIR: "default" }).dropped.length, 0);
});
