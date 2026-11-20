import { spawn, execFile } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { ASK_DESCRIPTION, ASK_SCHEMA, type Run } from "./ask.js";
import { getModel, type McpServer } from "./config.js";
import type { Emit } from "./chat.js";
import { usageOf } from "./usage.js";
import { attachLocalImages, roots } from "./localImages.js";
import { claudeBin } from "./claudeSetup.js";
import { recordClaudeRate } from "./planUsage.js";

// Bạn đang chạy trong CAD Studio (web), KHÔNG phải Claude Code: người dùng không gõ được /permissions hay lệnh "/" nào.
const SHELL_OFF = "Bạn đang chạy trong CAD Studio, không có công cụ chạy lệnh (Bash/PowerShell/Python). " +
  "Nếu việc cần chạy script hay lệnh, ĐỪNG bảo người dùng gõ /permissions hay lệnh / nào (CAD Studio không có). " +
  "Hãy nói: chuột phải vào dự án ở cột trái > bật \"Cho agent chạy lệnh\", rồi nhắn lại để bạn làm tiếp; hoặc làm bằng tool MCP nếu được. " +
  "Chạy lệnh chỉ có khi đang mở một dự án có thư mục.";
const SHELL_ON = "Dự án này đã bật \"Cho agent chạy lệnh\": bạn có công cụ Bash, thư mục làm việc là thư mục dự án. " +
  "Chỉ đọc/ghi trong thư mục dự án; dữ liệu nằm ngoài thì nhờ người dùng chép vào dự án. Không cài phần mềm, không xóa file ngoài dự án.";
const SYSTEM = process.env.CHAT_SYSTEM ??
  "Bạn là trợ lý điều khiển AutoCAD qua các tool MCP. Trả lời bằng tiếng Việt, ngắn gọn. " +
  "Trước khi sửa bản vẽ hãy đọc/đo để chắc chắn, và nói rõ bạn đã thay đổi gì. " +
  "Khi một tool chỉ trả đường dẫn file ảnh (\"inline\": false), hãy dùng công cụ Read mở file đó để xem ảnh trước khi mô tả. " +
  "Khi cần người dùng chọn giữa vài phương án rời rạc (xác nhận, chọn hướng, có/không), hãy gọi tool mcp__ask__ask_user để hiện bảng lựa chọn, đừng liệt kê bằng chữ rồi chờ họ gõ.";
const WORK = join(tmpdir(), "cad-web-cli");
const ASK_MCP = fileURLToPath(new URL("./ask-mcp.mjs", import.meta.url));

export function cliVersion(): Promise<string | null> {
  return new Promise(res => execFile(claudeBin(), ["--version"], { timeout: 8000 }, (e, out) => res(e ? null : out.trim())));
}

/** Chuẩn hóa nội dung tool_result của CLI về dạng web hiểu: [{type:"text"|"image",...}] */
function normalize(content: any): any[] {
  if (typeof content === "string") return [{ type: "text", text: content }];
  return (content ?? []).map((c: any) => c.type === "image"
    ? { type: "image", mimeType: c.source?.media_type, data: c.source?.data }
    : { type: "text", text: c.text ?? JSON.stringify(c) });
}

/**
 * Bộ đọc NDJSON của `claude -p --output-format stream-json` -> sự kiện cho web.
 * Dùng chung cho cả lúc chạy ngay trên server lẫn lúc chạy dưới máy người dùng, vì định dạng y hệt.
 */
function reader(emit: Emit, names: Record<string, string>, sessionId?: string) {
  let sid = sessionId, buf = "", finished = false;
  const seen = new Set<string>();
  const askIds = new Set<string>();   // tool ask_user hiện bằng thẻ câu hỏi riêng, không hiện như thẻ tool

  const handle = (ev: any) => {
    if (ev.session_id) sid = ev.session_id;
    if (ev.type === "stream_event" && ev.event?.delta?.type === "text_delta") emit("text", ev.event.delta.text);
    else if (ev.type === "assistant") {
      for (const b of ev.message?.content ?? []) if (b.type === "tool_use" && !seen.has(b.id)) {
        seen.add(b.id);
        const m = /^mcp__([a-z0-9]+)__(.+)$/.exec(String(b.name));
        if (m && m[1] === "ask") { askIds.add(b.id); continue; }
        emit("tool_use", { id: b.id, name: m ? m[2] : b.name, server: m ? names[m[1]] ?? m[1] : undefined, input: b.input });
      }
    } else if (ev.type === "user") {
      for (const b of Array.isArray(ev.message?.content) ? ev.message.content : []) if (b.type === "tool_result" && !askIds.has(b.tool_use_id))
        emit("tool_result", { id: b.tool_use_id, isError: !!b.is_error, content: attachLocalImages(normalize(b.content)) });
    } else if (ev.type === "rate_limit_event") {
      recordClaudeRate(ev.rate_limit_info);
    } else if (ev.type === "result") {
      finished = true;
      if (ev.usage) emit("usage", usageOf(ev.usage, ev.total_cost_usd));
      if (ev.is_error) emit("error", String(ev.result ?? "Claude CLI báo lỗi"));
    }
  };

  return {
    /** Nạp thêm một mẩu stdout; tự cắt theo dòng, dòng dở để lại chờ mẩu sau. */
    feed(text: string) {
      buf += text;
      let i: number;
      while ((i = buf.indexOf("\n")) >= 0) {
        const line = buf.slice(0, i).trim(); buf = buf.slice(i + 1);
        if (line) try { handle(JSON.parse(line)); } catch { /* dòng không phải JSON */ }
      }
    },
    get sessionId() { return sid; },
    get finished() { return finished; },
  };
}

/** Tên hiển thị của từng MCP, để thẻ tool ghi đúng tên server. */
const nameMap = (servers: McpServer[]) => Object.fromEntries(servers.map(s => [s.id, s.name]));

export type CliArgs = {
  prompt: string; sessionId?: string; allowed: string[]; emit: Emit; signal: AbortSignal; model?: string;
  ask?: { run: Run; url: string };
  serverList?: McpServer[];                 // MCP trên máy CAD của tài khoản; không có MCP chung của gateway
  att?: { dir: string; files: string[] };   // ảnh người dùng đính kèm (file tạm của lượt này)
  project?: { name: string; dir: string; shell?: boolean };
  effort?: string;                          // --effort của Claude CLI (low|medium|high|xhigh|max)  // dự án: CLI chạy trong thư mục này và được đọc file trong đó
};

/**
 * Chạy một lượt chat bằng Claude CLI **ngay trên máy này**, dùng lần đăng nhập `claude auth login` của máy này.
 * Gateway cục bộ và MCP (qua AutoCAD MCP Launcher) đều ở cùng một máy, nên không cần cầu nối tới máy khác.
 */
export function runCliLocal(a: CliArgs): Promise<string | undefined> {
  const { prompt: prompt0, sessionId, allowed, emit, signal, ask, att } = a;
  const model = a.model ?? getModel();
  let prompt = prompt0;
  mkdirSync(WORK, { recursive: true });
  const mcpFile = join(WORK, "mcp.json");
  const servers = (a.serverList ?? []).filter(s => s.enabled);
  const mcpServers: Record<string, unknown> = Object.fromEntries(servers.map(s => [s.id, s.transport === "stdio"
    ? { type: "stdio", command: s.command, args: s.args ?? [], env: s.env ?? {} }
    : { type: "http", url: s.url, ...(s.token ? { headers: { Authorization: `Bearer ${s.token}` } } : {}) }]));
  if (ask) mcpServers.ask = { type: "stdio", command: process.execPath, args: [ASK_MCP], env: {
    ASK_URL: ask.url, ASK_TOKEN: ask.run.token, ASK_DESCRIPTION: ASK_DESCRIPTION, ASK_SCHEMA: JSON.stringify(ASK_SCHEMA) } };
  writeFileSync(mcpFile, JSON.stringify({ mcpServers }), { mode: 0o600 });  // có thể chứa token nên chỉ chủ file đọc được
  const names = nameMap(servers);
  const allow = servers.flatMap(s => allowed.length ? allowed.map(n => `mcp__${s.id}__${n}`) : [`mcp__${s.id}`]);
  if (ask) allow.push("mcp__ask__ask_user");
  // Cho CLI mở ảnh (Read) nhưng CHỈ trong thư mục ảnh cho phép; mọi đường dẫn khác bị từ chối (CLI không hỏi quyền ở chế độ -p).
  const imageRoots = roots();
  for (const r of imageRoots) allow.push(`Read(${r.replace(/\\/g, "/")}/**)`);
  if (att) allow.push(`Read(${att.dir.replace(/\\/g, "/")}/**)`);   // đúng thư mục tạm của lượt này, không rộng hơn
  const proj = a.project;
  if (proj) for (const t of ["Read", "Glob", "Grep", "Write", "Edit"]) allow.push(`${t}(${proj.dir.replace(/\\/g, "/")}/**)`);
  if (proj?.shell) allow.push("Bash");   // người dùng đã bật "Cho agent chạy lệnh" cho dự án này
  if (att) prompt += `\n\n[Người dùng đã đính kèm ${att.files.length} ảnh. Hãy dùng công cụ Read mở từng file dưới đây để xem trước khi trả lời:\n${att.files.map(f => `- ${f}`).join("\n")}]`;

  const args = [
    "-p", "--output-format", "stream-json", "--verbose", "--include-partial-messages",
    "--mcp-config", mcpFile, "--strict-mcp-config",
    "--tools", proj ? `Read,Glob,Grep,Write,Edit${proj.shell ? ",Bash" : ""}` : imageRoots.length || att ? "Read" : "",    // chỉ có Read (giới hạn ở thư mục ảnh); khóa mọi công cụ sửa file/chạy lệnh
    "--allowedTools", allow.join(","),
    "--disable-slash-commands",
    "--append-system-prompt", proj ? `${SYSTEM}
Đang làm việc trong dự án "${proj.name}", thư mục ${proj.dir}. Hồ sơ, bản vẽ tham chiếu của dự án nằm trong thư mục này; dùng Glob/Grep/Read để tìm và đọc khi cần. File bạn tạo ra (báo cáo, bảng tính, DXF, ảnh xuất…) phải lưu trong thư mục này, không lưu nơi khác.
${proj.shell ? SHELL_ON : SHELL_OFF}` : `${SYSTEM}
${SHELL_OFF}`,
    "--model", model,
    ...(a.effort ? ["--effort", a.effort] : []),
    ...(sessionId ? ["--resume", sessionId] : []),
  ];

  return new Promise((resolve, reject) => {
    // MCP_TOOL_TIMEOUT: tool ask_user có thể chờ người dùng rất lâu, mặc định của CLI sẽ cắt ngang.
    const p = spawn(claudeBin(), args, { cwd: proj?.dir ?? WORK, stdio: ["pipe", "pipe", "pipe"], windowsHide: true, env: { ...process.env, MCP_TOOL_TIMEOUT: "1800000" } });
    signal.addEventListener("abort", () => p.kill());
    p.stdin.end(prompt);                             // qua stdin để khỏi dính giới hạn/escape của dòng lệnh

    const rd = reader(emit, names, sessionId);
    let err = "";
    p.stdout.setEncoding("utf8").on("data", (d: string) => rd.feed(d));
    p.stderr.setEncoding("utf8").on("data", d => { err += d; });
    p.on("error", e => reject(e));
    p.on("close", code => {
      if (signal.aborted) return resolve(rd.sessionId);
      if (!rd.finished && code !== 0) return reject(new Error(err.trim() || `claude thoát với mã ${code}`));
      resolve(rd.sessionId);
    });
  });
}
