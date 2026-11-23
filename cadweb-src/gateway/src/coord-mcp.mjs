// Tiến trình MCP (stdio) cực nhỏ cho bảng điều phối, do Claude CLI/Codex khởi chạy cho mỗi lượt chat (khuôn theo ask-mcp.mjs).
// Năm tool coord_status/claim/release/post/task; mỗi lần gọi chỉ chuyển nguyên tham số về gateway (POST COORD_URL kèm
// COORD_TOKEN của lượt). Mọi logic và việc ghi .cadstudio/coord.json nằm ở gateway (coord.ts).
import http from "node:http";
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema } from "@modelcontextprotocol/sdk/types.js";

const URL_ = process.env.COORD_URL, TOKEN = process.env.COORD_TOKEN;
const TOOLS = JSON.parse(process.env.COORD_TOOLS ?? "[]");

const post = (urlStr, headers, body) => new Promise((resolve, reject) => {
  const u = new URL(urlStr);
  const req = http.request({ hostname: u.hostname, port: u.port, path: u.pathname, method: "POST", timeout: 30_000, headers: { ...headers, "content-length": Buffer.byteLength(body) } }, res => {
    let data = "";
    res.setEncoding("utf8");
    res.on("data", d => { data += d; });
    res.on("end", () => resolve({ status: res.statusCode ?? 0, json: (() => { try { return JSON.parse(data); } catch { return {}; } })() }));
    res.on("error", reject);
  });
  req.on("timeout", () => req.destroy(new Error("gateway không trả lời")));
  req.on("error", reject);
  req.end(body);
});
const text = (t, isError = false) => ({ content: [{ type: "text", text: t }], ...(isError ? { isError: true } : {}) });

const server = new Server({ name: "coord", version: "1.0.0" }, { capabilities: { tools: {} } });
server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools: TOOLS }));
server.setRequestHandler(CallToolRequestSchema, async req => {
  if (!TOOLS.some(t => t.name === req.params.name)) return text("Tool không tồn tại.", true);
  if (!URL_ || !TOKEN) return text("Thiếu COORD_URL hoặc COORD_TOKEN.", true);
  try {
    const r = await post(URL_, { "content-type": "application/json", "x-coord-token": TOKEN }, JSON.stringify({ tool: req.params.name, args: req.params.arguments ?? {} }));
    const j = r.json;
    return r.status === 200 && typeof j.text === "string" ? text(j.text, !!j.isError) : text(j.error ?? `Gateway trả lỗi ${r.status}.`, true);
  } catch (e) {
    return text(`Không gọi được gateway: ${e?.message ?? e}`, true);
  }
});
await server.connect(new StdioServerTransport());
process.stdin.on("close", () => process.exit(0));
