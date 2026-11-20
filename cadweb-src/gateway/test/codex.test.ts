import { test } from "node:test";
import assert from "node:assert/strict";
import { codexArgs, codexMapper, INSTRUCTIONS } from "../src/codex.js";
import { DEFAULT_CODEX_MODEL, parseCodexModels } from "../src/codexmodels.js";

const http = { id: "dutoan", name: "dutoan", enabled: true, transport: "http" as const, url: "http://127.0.0.1:8764/dutoan/mcp" };
const withToken = { id: "remote", name: "Remote", enabled: true, transport: "http" as const, url: "https://x.example/mcp", token: "bi-mat-123" };
const stdio = { id: "tool", name: "Tool", enabled: true, transport: "stdio" as const, command: "C:\\Program Files\\x\\y.exe", args: ["--a", "b c"], env: { K: 'v"q' } };
const cfgValues = (args: string[]) => args.flatMap((a, i) => (args[i - 1] === "-c" ? [a] : []));

test("dòng lệnh Codex: cờ an toàn, MCP, phê duyệt sẵn, nối tiếp phiên", () => {
  const { args } = codexArgs({ model: DEFAULT_CODEX_MODEL, servers: [http], allowed: [] });
  assert.deepEqual(args.slice(0, 2), ["exec", "--json"]);
  assert.ok(args.includes("--ignore-user-config") && args.includes("--ignore-rules") && args.includes("--skip-git-repo-check"));
  for (const f of ["computer_use", "browser_use", "plugins", "hooks", "apps"]) assert.ok(args.some((a, i) => a === f && args[i - 1] === "--disable"), f);
  const c = cfgValues(args);
  assert.ok(c.includes('sandbox_mode="read-only"') && c.includes('approval_policy="never"'));
  assert.ok(c.includes('mcp_servers.dutoan.url="http://127.0.0.1:8764/dutoan/mcp"'));
  assert.ok(c.includes('mcp_servers.dutoan.default_tools_approval_mode="approve"'));
  assert.ok(c.includes("mcp_servers.dutoan.tool_timeout_sec=900"));
  assert.ok(!args.includes("-m"), "model mặc định thì không truyền -m");
  assert.equal(args.at(-1), "-");
  assert.ok(!args.includes("resume"));
});

test("nối tiếp phiên: resume đứng ngay sau exec, mã phiên đứng trước dấu - ở cuối; model riêng thì có -m", () => {
  const { args } = codexArgs({ sessionId: "01a1ec95-1db3-7c32-9987-223607be067c", model: "gpt-6.2-sol", servers: [], allowed: [] });
  assert.deepEqual(args.slice(0, 3), ["exec", "resume", "--json"]);
  assert.deepEqual(args.slice(-2), ["01a1ec95-1db3-7c32-9987-223607be067c", "-"]);
  assert.ok(args.some((a, i) => a === "gpt-6.2-sol" && args[i - 1] === "-m"));
});

test("token MCP đi qua biến môi trường, không nằm trên dòng lệnh", () => {
  const { args, env } = codexArgs({ model: DEFAULT_CODEX_MODEL, servers: [withToken], allowed: [] });
  assert.equal(env.CAD_MCP_TOKEN_REMOTE, "bi-mat-123");
  assert.ok(!args.join(" ").includes("bi-mat-123"));
  assert.ok(cfgValues(args).includes('mcp_servers.remote.bearer_token_env_var="CAD_MCP_TOKEN_REMOTE"'));
});

test("MCP chạy bằng lệnh: đường dẫn Windows và dấu nháy được thoát đúng chuẩn TOML", () => {
  const c = cfgValues(codexArgs({ model: DEFAULT_CODEX_MODEL, servers: [stdio], allowed: [] }).args);
  assert.ok(c.includes('mcp_servers.tool.command="C:\\\\Program Files\\\\x\\\\y.exe"'));
  assert.ok(c.includes('mcp_servers.tool.args=["--a","b c"]'));
  assert.ok(c.includes('mcp_servers.tool.env.K="v\\"q"'));
});

test("giới hạn tool: enabled_tools theo ALLOWED_TOOLS; server hỏi người dùng luôn có và không bị lọc", () => {
  const c = cfgValues(codexArgs({ model: DEFAULT_CODEX_MODEL, servers: [http], allowed: ["list_projects", "get_thvt"], ask: { run: { token: "tk" }, url: "http://127.0.0.1:1/internal/ask" } }).args);
  assert.ok(c.includes('mcp_servers.dutoan.enabled_tools=["list_projects","get_thvt"]'));
  assert.ok(c.includes('mcp_servers.ask.env.ASK_TOKEN="tk"'));
  assert.ok(c.includes('mcp_servers.ask.default_tools_approval_mode="approve"'));
  assert.ok(c.includes("mcp_servers.ask.tool_timeout_sec=1800"));
  assert.ok(!c.some(x => x.startsWith("mcp_servers.ask.enabled_tools")));
  assert.match(INSTRUCTIONS, /KHÔNG chạy lệnh shell/);
});

// Các dòng dưới đây lấy từ lần chạy thật `codex exec --json` (rút gọn)
const REAL = [
  '{"type":"thread.started","thread_id":"01a1ec95-ba3c-73c1-8492-153e443e7677"}',
  '{"type":"turn.started"}',
  '{"type":"item.completed","item":{"id":"item_0","type":"agent_message","text":"Tôi sẽ tìm và gọi `list_projects`."}}',
  '{"type":"item.started","item":{"id":"item_1","type":"mcp_tool_call","server":"dutoan","tool":"list_projects","arguments":{},"result":null,"error":null,"status":"in_progress"}}',
  '{"type":"item.completed","item":{"id":"item_1","type":"mcp_tool_call","server":"dutoan","tool":"list_projects","arguments":{},"result":{"content":[{"type":"text","text":"{\\n  \\"projects\\": []\\n}"}],"structured_content":null},"error":null,"status":"completed"}}',
  '{"type":"item.completed","item":{"id":"item_2","type":"agent_message","text":"Có 0 dự án."}}',
  '{"type":"turn.completed","usage":{"input_tokens":83703,"cached_input_tokens":68736,"cache_write_input_tokens":0,"output_tokens":93,"reasoning_output_tokens":0}}',
];

test("đọc sự kiện thật của Codex: văn bản, thẻ tool, token, thread_id", () => {
  const ev: [string, any][] = [];
  const m = codexMapper((e, d) => { ev.push([e, d]); }, { dutoan: "Dự toán" });
  for (const l of REAL) m.handle(JSON.parse(l));
  assert.equal(m.threadId(), "01a1ec95-ba3c-73c1-8492-153e443e7677");
  assert.equal(m.finished(), true);
  const kinds = ev.map(e => e[0]);
  assert.deepEqual(kinds, ["text", "tool_use", "tool_result", "text", "usage"]);
  assert.deepEqual(ev[1][1], { id: "item_1", name: "list_projects", server: "Dự toán", input: {} });
  assert.equal(ev[2][1].isError, false);
  assert.match(ev[2][1].content[0].text, /projects/);
  assert.equal(ev[3][1], "Có 0 dự án.", "có tool xen giữa thì không thêm dòng trống");
  // input_tokens của Codex đã gồm phần cached: tách ra để không đếm hai lần
  assert.deepEqual(ev[4][1], { input: 83703 - 68736, output: 93, cacheRead: 68736, cacheWrite: 0 });
});

test("tool bị từ chối hiện lỗi; hai tin nhắn liền nhau cách một dòng trống; tool ask_user không hiện thẻ tool", () => {
  const ev: [string, any][] = [];
  const m = codexMapper((e, d) => { ev.push([e, d]); });
  m.handle({ type: "item.completed", item: { id: "a", type: "agent_message", text: "Một" } });
  m.handle({ type: "item.completed", item: { id: "b", type: "agent_message", text: "Hai" } });
  m.handle({ type: "item.started", item: { id: "c", type: "mcp_tool_call", server: "x", tool: "t", arguments: {} } });
  m.handle({ type: "item.completed", item: { id: "c", type: "mcp_tool_call", server: "x", tool: "t", arguments: {}, result: null, error: { message: "MCP tool call requires approval" }, status: "failed" } });
  m.handle({ type: "item.started", item: { id: "d", type: "mcp_tool_call", server: "ask", tool: "ask_user", arguments: {} } });
  m.handle({ type: "item.completed", item: { id: "d", type: "mcp_tool_call", server: "ask", tool: "ask_user", arguments: {}, result: { content: [] }, status: "completed" } });
  m.handle({ type: "turn.failed", error: { message: "hết hạn đăng nhập" } });
  assert.deepEqual(ev.map(e => e[0]), ["text", "text", "tool_use", "tool_result", "error"]);
  assert.equal(ev[1][1], "\n\nHai");
  assert.deepEqual([ev[3][1].isError, ev[3][1].content[0].text], [true, "MCP tool call requires approval"]);
  assert.equal(ev[4][1], "hết hạn đăng nhập");
});

test("danh mục model: chỉ lấy model hiển thị, bỏ model ẩn và tên lạ", () => {
  const list = parseCodexModels(JSON.stringify([
    { slug: "gpt-6.2-sol", display_name: "GPT-6.2-Sol", visibility: "list" },
    { slug: "gpt-reserve", display_name: "GPT-Reserve", visibility: "hide" },
    { slug: "--bad flag", display_name: "x", visibility: "list" },
  ]));
  assert.deepEqual(list, [{ id: "gpt-6.2-sol", label: "GPT-6.2-Sol" }]);
  assert.throws(() => parseCodexModels("không phải json"));
});
