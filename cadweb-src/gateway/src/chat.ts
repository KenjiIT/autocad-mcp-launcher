import Anthropic from "@anthropic-ai/sdk";
import { tempClients } from "./mcp.js";
import { usageOf } from "./usage.js";
import { ASK_DESCRIPTION, ASK_SCHEMA, ASK_TOOL_NAME, type Run } from "./ask.js";
import { getKey, getModel, type McpServer } from "./config.js";
import { attachLocalImages } from "./localImages.js";

const MAX_STEPS = Number(process.env.CHAT_MAX_STEPS ?? 20);
const MAX_TEXT = 20_000; // cắt kết quả tool quá dài để khỏi tốn token
const SYSTEM = process.env.CHAT_SYSTEM ??
  "Bạn là trợ lý điều khiển AutoCAD qua các tool MCP. Trả lời bằng tiếng Việt, ngắn gọn. " +
  "Trước khi sửa bản vẽ hãy đọc/đo để chắc chắn, và nói rõ bạn đã thay đổi gì. " +
  "Khi cần người dùng chọn giữa vài phương án rời rạc (xác nhận, chọn hướng, có/không), hãy gọi tool ask_user để hiện bảng lựa chọn, đừng liệt kê bằng chữ rồi chờ họ gõ.";

export type Emit = (event: string, data: unknown) => void;


export const anthropic = () => new Anthropic({ apiKey: getKey() });

function toBlocks(content: any[] | undefined): Anthropic.ToolResultBlockParam["content"] {
  const out: any[] = [];
  for (const c of content ?? []) {
    if (c.type === "image") out.push({ type: "image", source: { type: "base64", media_type: c.mimeType, data: c.data } });
    else {
      let t: string = c.text ?? JSON.stringify(c);
      if (t.length > MAX_TEXT) t = t.slice(0, MAX_TEXT) + `\n…[đã cắt ${t.length - MAX_TEXT} ký tự]`;
      out.push({ type: "text", text: t });
    }
  }
  return out.length ? out : [{ type: "text", text: "(trống)" }];
}

/** Chạy vòng lặp chat + tool. Trả về toàn bộ messages sau lượt này. `servers`: danh sách server riêng của lượt này (MCP ở máy CAD của tài khoản); không có thì dùng danh sách chung của gateway. */
export async function runChat(
  history: Anthropic.MessageParam[], allowed: (n: string) => boolean, emit: Emit, signal: AbortSignal, model: string = getModel(), run?: Run, servers: McpServer[] = [],
): Promise<Anthropic.MessageParam[]> {
  const pool = tempClients(servers);
  try { return await chatLoop(history, allowed, emit, signal, model, run, servers, (id, fn) => pool.with(id, fn)); }
  finally { await pool.close(); }
}

async function chatLoop(
  history: Anthropic.MessageParam[], allowed: (n: string) => boolean, emit: Emit, signal: AbortSignal, model: string, run: Run | undefined,
  serverList: McpServer[], withSrv: <T>(id: string, fn: (c: import("@modelcontextprotocol/sdk/client/index.js").Client) => Promise<T>) => Promise<T>,
): Promise<Anthropic.MessageParam[]> {
  // Gộp tool của mọi server đang bật. Tên gửi cho Claude là "<id>__<tool>" để hai server trùng tên tool không đè nhau.
  const tools: Anthropic.Tool[] = [];
  const route = new Map<string, { id: string; server: string; tool: string }>();
  await Promise.all(serverList.filter(s => s.enabled).map(async s => {
    try {
      const listed = await withSrv(s.id, c => c.listTools());
      for (const t of listed.tools) {
        if (!allowed(t.name)) continue;
        const name = `${s.id}__${t.name}`.slice(0, 64);
        route.set(name, { id: s.id, server: s.name, tool: t.name });
        tools.push({ name, description: t.description ?? "", input_schema: t.inputSchema as Anthropic.Tool.InputSchema });
      }
    } catch { emit("notice", `Server MCP "${s.name}" không nối được nên bị bỏ qua lượt này.`); }
  }));
  if (run) tools.push({ name: ASK_TOOL_NAME, description: ASK_DESCRIPTION, input_schema: ASK_SCHEMA as unknown as Anthropic.Tool.InputSchema });
  const messages = [...history];
  const ai = anthropic();

  for (let step = 0; step < MAX_STEPS; step++) {
    const stream = ai.messages.stream(
      { model, max_tokens: 8192, system: SYSTEM, tools, messages }, { signal });
    stream.on("text", d => emit("text", d));
    const msg = await stream.finalMessage();
    emit("usage", usageOf(msg.usage));
    messages.push({ role: "assistant", content: msg.content });
    if (msg.stop_reason !== "tool_use") break;

    const results: Anthropic.ToolResultBlockParam[] = [];
    for (const b of msg.content) {
      if (b.type !== "tool_use") continue;
      if (run && b.name === ASK_TOOL_NAME) {   // câu hỏi cho người dùng: hiện thẻ lựa chọn (do run.ask phát), không phải thẻ tool
        let text: string, isError = false;
        try { text = await run.ask(b.input, signal); } catch (e: any) { text = e?.message ?? String(e); isError = true; }
        results.push({ type: "tool_result", tool_use_id: b.id, is_error: isError, content: text });
        continue;
      }
      const r = route.get(b.name);
      emit("tool_use", { id: b.id, name: r?.tool ?? b.name, server: r?.server, input: b.input });
      let res: any;
      try {
        res = r
          ? await withSrv(r.id, c => c.callTool({ name: r.tool, arguments: b.input as any }, undefined, { timeout: 120_000, signal }))
          : { isError: true, content: [{ type: "text", text: "tool không tồn tại hoặc không được phép" }] };
      } catch (e) {
        res = { isError: true, content: [{ type: "text", text: String(e) }] };
      }
      // Ảnh đọc từ file (tool chỉ trả đường dẫn) vừa hiển thị cho người dùng vừa đưa cho Claude xem.
      const withImages = attachLocalImages(res.content);
      emit("tool_result", { id: b.id, isError: !!res.isError, content: withImages });
      results.push({ type: "tool_result", tool_use_id: b.id, is_error: !!res.isError, content: toBlocks(withImages) });
    }
    messages.push({ role: "user", content: results });
    if (step === MAX_STEPS - 1) emit("notice", `Dừng sau ${MAX_STEPS} bước.`);
  }
  return messages;
}
