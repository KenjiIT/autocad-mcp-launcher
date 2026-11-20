// MÔ HÌNH THỬ: một server MCP chạy trên "máy khác", mở ra mạng và bắt buộc token Bearer.
// Chạy: REMOTE_TOKEN=xxx npx tsx demo/remote-mcp.ts   (mặc định cổng 8791, nghe mọi địa chỉ mạng)
import http from "node:http";
import os from "node:os";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";

const TOKEN = process.env.REMOTE_TOKEN ?? "";
const PORT = Number(process.env.PORT ?? 8791);
if (!TOKEN) { console.error("Đặt REMOTE_TOKEN."); process.exit(1); }

function build() {
  const s = new McpServer({ name: "remote-demo", version: "0.1.0" });
  s.tool("whoami", "Cho biết máy nào đang chạy server này (để chứng minh lệnh gọi đã đi qua mạng).", async () => ({
    content: [{ type: "text", text: JSON.stringify({ host: os.hostname(), platform: os.platform(), time: new Date().toISOString() }) }],
  }));
  return s;
}

http.createServer(async (req, res) => {
  console.log(`${new Date().toISOString()} ${req.method} ${req.url} từ ${req.socket.remoteAddress}`);
  if (req.headers.authorization !== `Bearer ${TOKEN}`) { res.writeHead(401).end("unauthorized"); return; }
  if (req.url !== "/mcp" || req.method !== "POST") { res.writeHead(405).end(); return; }
  const chunks: Buffer[] = []; for await (const c of req) chunks.push(c as Buffer);
  const body = JSON.parse(Buffer.concat(chunks).toString() || "{}");
  const server = build();
  const t = new StreamableHTTPServerTransport({ sessionIdGenerator: undefined });  // không giữ phiên: mỗi lệnh độc lập
  res.on("close", () => { void t.close(); void server.close(); });
  await server.connect(t);
  await t.handleRequest(req, res, body);
}).listen(PORT, "0.0.0.0", () => console.log(`remote-demo MCP: http://0.0.0.0:${PORT}/mcp (cần token)`));
