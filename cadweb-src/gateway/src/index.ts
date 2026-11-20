import { serve } from "@hono/node-server";
import { serveStatic } from "@hono/node-server/serve-static";
import { readFileSync } from "node:fs";
import { join, relative } from "node:path";
import { Hono } from "hono";
import { cors } from "hono/cors";
import { streamSSE } from "hono/streaming";
import { statusOf, tempClients } from "./mcp.js";
import { getEngine, getKey, getModels, modelFor, publicConfig, saveConfig, type McpServer } from "./config.js";
import { runChat } from "./chat.js";
import { friendly } from "./errors.js";
import { runCliLocal, cliVersion } from "./cli.js";
import { runCodex, codexVersion } from "./codex.js";
import { ensureCodexModels } from "./codexmodels.js";
import { claudeStatus, startInstall, startLogin } from "./claudeSetup.js";
import { Run, runByToken, runForAnswer } from "./ask.js";
import { AttachmentError, rebuildContent, splitContent, stage, type Staged, type UserImage } from "./attachments.js";
import { deleteConversation, getConversation, listConversations, ownsCliSession, putConversation, readImage, rememberCliSession, userScope, validFile, validId } from "./store.js";

// Bản LOCAL: web + gateway + MCP chạy trên CÙNG một máy, cạnh AutoCAD MCP Launcher đang mở sẵn ở 127.0.0.1:8764.
// Không có đăng nhập/tài khoản (một người dùng local), không có mô hình "máy CAD từ xa" qua WebSocket: gọi thẳng MCP.
const PORT = Number(process.env.PORT ?? 8788);
const HOST = process.env.HOST ?? "127.0.0.1";
const ALLOWED = (process.env.ALLOWED_TOOLS ?? "").split(",").map(s => s.trim()).filter(Boolean);
const ORIGINS = (process.env.CORS_ORIGIN ?? "http://localhost:5174").split(",").map(s => s.trim().replace(/\/+$/, "")).filter(Boolean);

// MCP của chính máy này, phục vụ bởi AutoCAD MCP Launcher. Cấu hình qua LOCAL_MCP="key:Tên hiện,key2:Tên 2" (mặc định
// ba MCP chuẩn của launcher); LOCAL_MCP_BASE đổi địa chỉ gateway của launcher nếu không phải cổng mặc định.
const LOCAL_MCP_BASE = (process.env.LOCAL_MCP_BASE ?? "http://127.0.0.1:8764").replace(/\/+$/, "");
const DEFAULT_LOCAL_MCP = "beiming:AutoCAD Beiming,puran:AutoCAD Puran,dutoan:Dự toán";
function localServers(): McpServer[] {
  return (process.env.LOCAL_MCP ?? DEFAULT_LOCAL_MCP).split(",").map(s => s.trim()).filter(Boolean).map(entry => {
    const i = entry.indexOf(":");
    const key = (i > 0 ? entry.slice(0, i) : entry).trim();
    const name = (i > 0 ? entry.slice(i + 1) : entry).trim();
    return { id: key, name, enabled: true, transport: "http", url: `${LOCAL_MCP_BASE}/${key}/mcp` };
  });
}
/** MCP của máy này, cộng với close() không-làm-gì (giữ cho khớp hình dạng dùng ở các route dưới). */
function openMcp(): { servers: McpServer[]; close: () => void } { return { servers: localServers(), close: () => {} }; }

const app = new Hono();
app.use("/api/*", cors({ origin: ORIGINS, credentials: true }));

const OWNER = "local";
const SCOPE = userScope(OWNER);

// CLI/Codex chạy NGAY TRÊN MÁY NÀY (cùng máy với gateway), nên MCP `ask` gọi ngược về loopback, không cần địa chỉ công khai.
const ASK_URL = `http://127.0.0.1:${PORT}/internal/ask`;

app.get("/api/health", async c => {
  const mcp = openMcp();
  try {
    const list = await Promise.all(mcp.servers.map(async s => { const st = await statusOf(s); return { id: s.id, name: s.name, ok: st.ok, tools: st.tools.length, error: st.error }; }));
    const tools = list.reduce((n, x) => n + x.tools, 0);
    if (list.some(x => x.ok)) return c.json({ ok: true, tools, servers: list });
    return c.json({ ok: false, tools: 0, servers: list, error: `Không nối được MCP nào (${list.map(x => x.name).join(", ")}). Mở AutoCAD MCP Launcher và bật "Bật kết nối cho agent".` }, 503);
  } finally { mcp.close(); }
});

let skillCache: { at: number; list: { name: string; description: string; server: string }[] } | null = null;

app.get("/api/models", async c => {
  if (getEngine() === "codex") await ensureCodexModels();
  return c.json({ models: getModels(), default: getModels().find(m => m.id === publicConfig().model)?.id ?? getModels()[0].id });
});

app.get("/api/config", async c => c.json({ ...publicConfig(), cliVersion: await cliVersion(), codexVersion: await codexVersion() }));

app.put("/api/config", async c => {
  const b = await c.req.json().catch(() => ({}));
  const patch: { anthropicKey?: string; engine?: string } = {};
  if (b.engine === "cli" || b.engine === "api" || b.engine === "codex") patch.engine = b.engine;
  if (typeof b.anthropicKey === "string") patch.anthropicKey = b.anthropicKey;
  if (patch.anthropicKey) {
    try { await new (await import("@anthropic-ai/sdk")).default({ apiKey: patch.anthropicKey.trim() }).models.list({ limit: 1 }); }
    catch (e: any) { return c.json({ error: e?.status === 401 ? "Key không hợp lệ (Anthropic từ chối)." : `Không kiểm tra được key: ${friendly(e)}` }, 400); }
  }
  saveConfig(patch);
  return c.json({ ...publicConfig(), cliVersion: await cliVersion(), codexVersion: await codexVersion() });
});

// Cài và đăng nhập Claude CLI ngay trên máy này (chế độ Claude CLI cần cả hai).
app.get("/api/claude/status", async c => c.json(await claudeStatus()));
app.post("/api/claude/install", c => { const r = startInstall(); return r.error ? c.json(r, 500) : c.json({ ok: true }); });
app.post("/api/claude/login", c => { const r = startLogin(); return r.error ? c.json(r, 400) : c.json({ ok: true }); });

app.get("/api/skills", async c => {
  if (ALLOWED.length && !ALLOWED.includes("skills")) return c.json({ skills: [] });
  if (skillCache && skillCache.at > Date.now() - 60_000) return c.json({ skills: skillCache.list });
  const mcp = openMcp();
  const list: { name: string; description: string; server: string }[] = [];
  const pool = tempClients(mcp.servers);
  try {
    await Promise.all(mcp.servers.map(async s => {
      try {
        const tools = (await pool.with(s.id, cl => cl.listTools())).tools;
        if (!tools.some(t => t.name === "skills")) return;
        const res: any = await pool.with(s.id, cl => cl.callTool({ name: "skills", arguments: { operation: "list" } }, undefined, { timeout: 20_000 }));
        const j = JSON.parse(res.content?.find((x: any) => x.type === "text")?.text ?? "{}");
        for (const x of Array.isArray(j.skills) ? j.skills : []) if (x?.name) list.push({ name: String(x.name), description: String(x.description ?? ""), server: s.name });
      } catch { /* server lỗi thì bỏ qua phần gợi ý của nó */ }
    }));
  } finally { await pool.close(); mcp.close(); }
  skillCache = { at: Date.now(), list };
  return c.json({ skills: list });
});

app.get("/api/conversations", c => c.json({ conversations: listConversations(SCOPE) }));
app.get("/api/conversations/:id", c => {
  const id = c.req.param("id");
  const conv = validId(id) ? getConversation(SCOPE, id) : null;
  return conv ? c.json(conv) : c.json({ error: "Không tìm thấy cuộc trò chuyện." }, 404);
});
app.put("/api/conversations/:id", async c => {
  const id = c.req.param("id");
  if (!validId(id)) return c.json({ error: "id không hợp lệ" }, 400);
  const b = await c.req.json().catch(() => null);
  if (!b || typeof b !== "object") return c.json({ error: "Dữ liệu không hợp lệ" }, 400);
  const r = putConversation(SCOPE, id, b);
  return c.json({ id: r.id, title: r.title, updatedAt: r.updatedAt });
});
app.delete("/api/conversations/:id", c => {
  const id = c.req.param("id");
  if (!validId(id)) return c.json({ error: "id không hợp lệ" }, 400);
  deleteConversation(SCOPE, id);
  return c.json({ ok: true });
});
app.get("/api/files/:name", c => {
  const name = c.req.param("name");
  const f = validFile(name) ? readImage(SCOPE, name) : null;
  return f ? new Response(f.data, { headers: { "Content-Type": f.mime, "Cache-Control": "private, max-age=31536000, immutable" } }) : c.json({ error: "Không có file." }, 404);
});

app.post("/api/chat", async c => {
  if (getEngine() === "api" && !getKey()) return c.json({ error: "Chưa có API key. Vào tab Cài đặt để nhập, hoặc chuyển sang chế độ Claude CLI." }, 503);
  const body = await c.req.json().catch(() => ({}));
  if (!Array.isArray(body.messages) || !body.messages.length) return c.json({ error: "thiếu messages" }, 400);
  const mcp = openMcp();
  const routed = mcp.servers;
  const lastIdx = body.messages.map((m: any) => m?.role).lastIndexOf("user");
  let userText = "", userImages: UserImage[] = [];
  try {
    ({ text: userText, images: userImages } = splitContent(body.messages[lastIdx]?.content));
  } catch (e) {
    if (e instanceof AttachmentError) { mcp.close(); return c.json({ error: e.message }, 400); }
    throw e;
  }
  if (userImages.length) body.messages[lastIdx] = { role: "user", content: rebuildContent(userText, userImages) };
  return streamSSE(c, async s => {
    let staged: Staged | undefined;
    const ac = new AbortController();
    s.onAbort(() => ac.abort());
    const emit = (event: string, data: unknown) => s.writeSSE({ event, data: JSON.stringify(data) });
    const run = new Run(OWNER, emit);
    try {
      const engine = getEngine();
      if (engine === "cli" || engine === "codex") {
        staged = stage(userImages);
        const prompt = userText || (userImages.length ? "Hãy xem ảnh đính kèm." : "");
        if (!prompt) throw new Error("thiếu nội dung tin nhắn");
        const tag = engine === "codex" ? "codex:" : "";
        const asked = typeof body.sessionId === "string" ? body.sessionId : undefined;
        const resume = asked && ownsCliSession(SCOPE, tag + asked) ? asked : undefined;
        if (asked && !resume) await emit("notice", "Không nối lại được phiên trước đó của cuộc trò chuyện này, đã bắt đầu phiên mới.");
        const ask = { run, url: ASK_URL };
        const sessionId = engine === "codex"
          ? await runCodex(prompt, resume, ALLOWED, emit, ac.signal, modelFor(body.model), ask, routed, staged?.files)
          : await runCliLocal({ prompt, sessionId: resume, allowed: ALLOWED, emit, signal: ac.signal, model: modelFor(body.model), ask, serverList: routed, att: staged });
        if (sessionId) rememberCliSession(SCOPE, tag + sessionId);
        await emit("done", { messages: [], sessionId });
      } else {
        const messages = await runChat(body.messages, (name: string) => ALLOWED.length === 0 || ALLOWED.includes(name), emit, ac.signal, modelFor(body.model), run, routed);
        await emit("done", { messages });
      }
    } catch (e) {
      if (!ac.signal.aborted) await emit("error", friendly(e));
    } finally { run.close(); mcp.close(); staged?.cleanup(); }
  });
});

app.post("/api/ask/:id", async c => {
  const run = runForAnswer(c.req.param("id"), OWNER);
  const b = await c.req.json().catch(() => null);
  if (!run || !b) return c.json({ error: "Câu hỏi này không còn chờ trả lời." }, 404);
  const err = run.answer(c.req.param("id"), b.answers);
  return err ? c.json({ error: err }, 400) : c.json({ ok: true });
});

// Gọi từ tiến trình ask-mcp.mjs (con của Claude CLI/Codex, chạy ngay trên máy này), xác thực bằng token riêng của lượt chat.
app.post("/internal/ask", async c => {
  const run = runByToken(c.req.header("x-ask-token"));
  if (!run) return c.json({ error: "Token không hợp lệ hoặc lượt chat đã kết thúc." }, 401);
  const b = await c.req.json().catch(() => null);
  try { return c.json({ text: await run.ask(b, c.req.raw.signal) }); }
  catch (e: any) { return c.json({ error: e?.message ?? String(e) }, 400); }
});

// Bản đóng gói kèm launcher: không có Vite, gateway tự phục vụ web đã build (WEB_DIR) trên cùng một cổng.
const WEB_DIR = process.env.WEB_DIR;
if (WEB_DIR) {
  const root = relative(process.cwd(), WEB_DIR) || ".";
  app.use("/*", serveStatic({ root }));
  const index = readFileSync(join(WEB_DIR, "index.html"), "utf8");
  app.get("*", c => c.req.path.startsWith("/api/") || c.req.path.startsWith("/internal/") ? c.notFound() : c.html(index));
}

const server = serve({ fetch: app.fetch, hostname: HOST, port: PORT }, i => console.log(`cad-web-local gateway http://${HOST}:${i.port} (MCP trực tiếp từ ${LOCAL_MCP_BASE})`));
// `tsx watch` khởi động lại khi sửa file: bản cũ cần một lúc mới nhả cổng, nên thử lại thay vì sập.
let listenTries = 0;
server.on("error", (e: NodeJS.ErrnoException) => {
  if (e.code === "EADDRINUSE" && listenTries++ < 40) { setTimeout(() => server.listen(PORT, HOST), 500); return; }
  console.error(e.code === "EADDRINUSE" ? `Cổng ${PORT} đang bị chương trình khác giữ.` : e); process.exit(1);
});

process.on("unhandledRejection", e => console.error("unhandledRejection:", e));
for (const sig of ["SIGINT", "SIGTERM"] as const) process.on(sig, () => process.exit(0));
