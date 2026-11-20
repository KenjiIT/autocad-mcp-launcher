// Tiến trình MCP (stdio) cực nhỏ do Claude CLI khởi chạy cho mỗi lượt chat, chỉ có một tool: ask_user.
// Khi CLI gọi tool, tiến trình này gọi ngược về gateway (POST ASK_URL, kèm ASK_TOKEN của lượt chat) và chờ tới khi người
// dùng trả lời trên web. Không có logic nào khác; mọi kiểm tra nằm ở gateway (ask.ts).
import http from "node:http";
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema } from "@modelcontextprotocol/sdk/types.js";

const URL_ = process.env.ASK_URL, TOKEN = process.env.ASK_TOKEN;
const DESCRIPTION = process.env.ASK_DESCRIPTION ?? "Hỏi người dùng bằng bảng lựa chọn.";
const SCHEMA = JSON.parse(process.env.ASK_SCHEMA ?? '{"type":"object"}');
/**
 * POST JSON và chờ phản hồi KHÔNG giới hạn thời gian. Không dùng fetch: fetch của Node có hạn chờ phản hồi mặc định 300 giây
 * (UND_ERR_HEADERS_TIMEOUT), mà người dùng có thể mất nhiều phút mới trả lời, khi đó tool báo lỗi và agent kết thúc lượt.
 */
const post = (urlStr, headers, body) => new Promise((resolve, reject) => {
  const u = new URL(urlStr);
  const req = http.request({ hostname: u.hostname, port: u.port, path: u.pathname, method: "POST", headers: { ...headers, "content-length": Buffer.byteLength(body) } }, res => {
    let data = "";
    res.setEncoding("utf8");
    res.on("data", d => { data += d; });
    res.on("end", () => resolve({ status: res.statusCode ?? 0, json: (() => { try { return JSON.parse(data); } catch { return {}; } })() }));
    res.on("error", reject);
  });
  req.on("error", reject);
  req.end(body);
});
const text = (t, isError = false) => ({ content: [{ type: "text", text: t }], ...(isError ? { isError: true } : {}) });

const server = new Server({ name: "ask", version: "1.0.0" }, { capabilities: { tools: {} } });
server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools: [{ name: "ask_user", description: DESCRIPTION, inputSchema: SCHEMA }] }));
server.setRequestHandler(CallToolRequestSchema, async req => {
  if (req.params.name !== "ask_user") return text("Tool không tồn tại.", true);
  if (!URL_ || !TOKEN) return text("Thiếu ASK_URL hoặc ASK_TOKEN.", true);
  try {
    const r = await post(URL_, { "content-type": "application/json", "x-ask-token": TOKEN }, JSON.stringify(req.params.arguments ?? {}));
    const j = r.json;
    return r.status === 200 && typeof j.text === "string" ? text(j.text) : text(j.error ?? `Gateway trả lỗi ${r.status}.`, true);
  } catch (e) {
    return text(`Không gọi được gateway: ${e?.message ?? e}`, true);
  }
});
await server.connect(new StdioServerTransport());
process.stdin.on("close", () => process.exit(0));   // CLI đóng ống nối (kể cả khi bị kill) thì tự thoát, không để tiến trình mồ côi
