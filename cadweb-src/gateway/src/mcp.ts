import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";
import { StdioClientTransport, getDefaultEnvironment } from "@modelcontextprotocol/sdk/client/stdio.js";
import { McpError } from "@modelcontextprotocol/sdk/types.js";
import type { McpServer } from "./config.js";

const CONNECT_TIMEOUT_MS = 15000;

function transportFor(s: McpServer) {
  if (s.transport === "stdio") {
    if (!s.command) throw new Error("thiếu lệnh chạy");
    return new StdioClientTransport({ command: s.command, args: s.args ?? [], env: { ...getDefaultEnvironment(), ...(s.env ?? {}) } });
  }
  if (!s.url) throw new Error("thiếu URL");
  return new StreamableHTTPClientTransport(new URL(s.url), s.token ? { requestInit: { headers: { Authorization: `Bearer ${s.token}` } } } : undefined);
}

async function connectServer(s: McpServer): Promise<Client> {
  const c = new Client({ name: "cad-web-gateway", version: "0.2.0" });
  let timer: NodeJS.Timeout | undefined;
  try {
    await Promise.race([
      c.connect(transportFor(s)),
      new Promise((_, rej) => { timer = setTimeout(() => rej(new Error(`timeout: server không phản hồi sau ${CONNECT_TIMEOUT_MS / 1000}s`)), CONNECT_TIMEOUT_MS); }),
    ]);
  } catch (e) { await c.close().catch(() => {}); throw e; }
  finally { clearTimeout(timer); }
  return c;
}

export function tempClients(servers: McpServer[]) {
  const open = new Map<string, Promise<Client>>();
  const get = (id: string) => {
    const s = servers.find(x => x.id === id && x.enabled);
    if (!s) return Promise.reject(new Error("Server MCP không tồn tại hoặc đang tắt."));
    let p = open.get(id);
    if (!p) { p = connectServer(s); p.catch(() => open.delete(id)); open.set(id, p); }
    return p;
  };
  return {
    with: async <T>(id: string, fn: (c: Client) => Promise<T>): Promise<T> => fn(await get(id)),
    close: async () => { await Promise.all([...open.values()].map(p => p.then(c => c.close()).catch(() => {}))); open.clear(); },
  };
}

export type ToolInfo = { name: string; description?: string };
export type ServerStatus = { ok: boolean; tools: ToolInfo[]; error?: string };

/** Nối thử một server MCP và lấy danh sách tool. Không ném lỗi: trả về trạng thái kèm lý do dễ hiểu. */
export async function statusOf(s: McpServer): Promise<ServerStatus> {
  let c: Client | undefined;
  try {
    c = await connectServer(s);
    const r = await c.listTools();
    return { ok: true, tools: r.tools.map(t => ({ name: t.name, description: t.description })) };
  } catch (e) {
    const msg = String((e as Error)?.message ?? e);
    return { ok: false, tools: [], error:
      /timeout/i.test(msg) ? "Máy CAD không phản hồi. Kiểm tra launcher đang chạy và MCP này đã bật trên máy."
      : /404/.test(msg) ? "Máy CAD không có MCP này (launcher trả 404). Kiểm tra lại khóa MCP."
      : /401|403|unauthorized|forbidden/i.test(msg) ? "Máy CAD từ chối truy cập."
      : `Không nối được tới MCP trên máy CAD. (${msg.slice(0, 160)})` };
  } finally { await c?.close().catch(() => {}); }
}
