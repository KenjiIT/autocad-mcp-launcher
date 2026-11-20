import { spawn, execFile } from "node:child_process";
import { mkdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import type { McpServer } from "./config.js";
import type { Emit } from "./chat.js";
import { attachLocalImages } from "./localImages.js";
import { ASK_DESCRIPTION, ASK_SCHEMA, type Run } from "./ask.js";
import { CODEX_BIN, DEFAULT_CODEX_MODEL } from "./codexmodels.js";

// Chế độ chat bằng Codex CLI: `codex exec --json` (và `codex exec resume <thread_id>` để nối tiếp).
// Cấu hình MCP và chỉ dẫn đưa qua `-c`, kèm --ignore-user-config để không nạp hook, danh sách MCP hay cài đặt riêng của máy.

const WORK = join(tmpdir(), "cad-web-codex");
const ASK_MCP = fileURLToPath(new URL("./ask-mcp.mjs", import.meta.url));

export const INSTRUCTIONS =
  "Bạn là trợ lý điều khiển AutoCAD qua các tool MCP. Trả lời bằng tiếng Việt, ngắn gọn. " +
  "Trước khi sửa bản vẽ hãy đọc/đo để chắc chắn, và nói rõ bạn đã thay đổi gì. " +
  "Chỉ dùng các tool MCP được cấp: KHÔNG chạy lệnh shell và KHÔNG đọc hay ghi tệp trên máy. " +
  "Khi cần người dùng chọn giữa vài phương án rời rạc (xác nhận, chọn hướng, có/không), hãy gọi tool ask_user của MCP server `ask` để hiện bảng lựa chọn, đừng liệt kê bằng chữ rồi chờ họ gõ.";

export function codexVersion(): Promise<string | null> {
  return new Promise(res => execFile(CODEX_BIN, ["--version"], { timeout: 8000, windowsHide: true }, (e, out) => res(e ? null : out.trim())));
}

const toml = (v: unknown) => JSON.stringify(v);   // chuỗi hoặc mảng JSON cũng là TOML hợp lệ (có thoát \\ và \")

export type CodexArgsInput = {
  sessionId?: string; model: string; servers: McpServer[]; allowed: string[];
  ask?: { run: Pick<Run, "token">; url: string };
  images?: string[];   // đường dẫn ảnh người dùng đính kèm (file tạm do gateway ghi)
};

/** Dựng dòng lệnh và biến môi trường cho một lượt chat. Tách riêng để kiểm thử. */
export function codexArgs(o: CodexArgsInput): { args: string[]; env: Record<string, string> } {
  const env: Record<string, string> = {};
  const c: string[] = [];
  const set = (k: string, v: unknown) => c.push("-c", `${k}=${toml(v)}`);
  set("sandbox_mode", "read-only");
  set("approval_policy", "never");                // không có người duyệt trong chế độ này, nên tool MCP phải được duyệt sẵn (bên dưới)
  set("developer_instructions", INSTRUCTIONS);

  for (const s of o.servers) {
    const p = `mcp_servers.${s.id}`;
    if (s.transport === "http") {
      set(`${p}.url`, s.url);
      if (s.token) { const name = `CAD_MCP_TOKEN_${s.id.toUpperCase()}`; env[name] = s.token; set(`${p}.bearer_token_env_var`, name); }  // token không nằm trên dòng lệnh
    } else {
      set(`${p}.command`, s.command);
      set(`${p}.args`, s.args ?? []);
      for (const [k, v] of Object.entries(s.env ?? {})) set(`${p}.env.${k}`, v);
    }
    set(`${p}.default_tools_approval_mode`, "approve");
    set(`${p}.tool_timeout_sec`, 900);            // tool CAD có thể chạy lâu (đọc bản vẽ lớn), mặc định 60 giây là quá ngắn
    if (o.allowed.length) set(`${p}.enabled_tools`, o.allowed);
  }
  if (o.ask) {
    set("mcp_servers.ask.command", process.execPath);
    set("mcp_servers.ask.args", [ASK_MCP]);
    set("mcp_servers.ask.env.ASK_URL", o.ask.url);
    set("mcp_servers.ask.env.ASK_TOKEN", o.ask.run.token);
    set("mcp_servers.ask.env.ASK_DESCRIPTION", ASK_DESCRIPTION);
    set("mcp_servers.ask.env.ASK_SCHEMA", JSON.stringify(ASK_SCHEMA));
    set("mcp_servers.ask.default_tools_approval_mode", "approve");
    set("mcp_servers.ask.tool_timeout_sec", 1800);  // chờ người dùng trả lời
  }

  const args = [
    "exec", ...(o.sessionId ? ["resume"] : []),
    "--json", "--ignore-user-config", "--ignore-rules", "--skip-git-repo-check",
    // Tắt các tính năng điều khiển máy/trình duyệt/plugin: chỉ để agent dùng tool MCP của mình
    "--disable", "computer_use", "--disable", "browser_use", "--disable", "browser_use_external", "--disable", "apps",
    "--disable", "plugins", "--disable", "hooks", "--disable", "image_generation",
    ...c,
    ...(o.model && o.model !== DEFAULT_CODEX_MODEL ? ["-m", o.model] : []),
    ...(o.sessionId ? [o.sessionId] : []),
    ...(o.images ?? []).map(f => `--image=${f}`),   // dạng "=" để cờ nhiều giá trị không nuốt mất "-" phía sau
    "-",                                          // lời nhắc đọc từ stdin
  ];
  return { args, env };
}

/** Nội dung kết quả tool MCP (khối text/image) về dạng web hiểu. */
function normalize(content: any): any[] {
  if (typeof content === "string") return [{ type: "text", text: content }];
  return (Array.isArray(content) ? content : []).map((c: any) => c?.type === "image"
    ? { type: "image", mimeType: c.mimeType ?? c.mime_type, data: c.data }
    : { type: "text", text: c?.text ?? JSON.stringify(c) });
}

/** Chuyển từng dòng JSON của `codex exec --json` thành sự kiện cho web. */
export function codexMapper(emit: Emit, serverNames: Record<string, string> = {}) {
  let threadId: string | undefined;
  let sepNext = false;              // hai tin nhắn liền nhau (không có tool xen giữa) thì cách một dòng trống
  const hidden = new Set<string>(); // tool ask_user hiện bằng thẻ câu hỏi riêng
  let done = false;

  const handle = (ev: any) => {
    if (ev.type === "thread.started") threadId = ev.thread_id;
    else if (ev.type === "turn.completed") {
      done = true;
      const u = ev.usage ?? {};
      const cached = Math.min(Number(u.cached_input_tokens) || 0, Number(u.input_tokens) || 0);   // input_tokens của Codex đã gồm phần cached
      emit("usage", { input: Math.max(0, (Number(u.input_tokens) || 0) - cached), output: Number(u.output_tokens) || 0, cacheRead: cached, cacheWrite: Number(u.cache_write_input_tokens) || 0 });
    } else if (ev.type === "turn.failed") { done = true; emit("error", String(ev.error?.message ?? "Codex báo lỗi")); }
    else if (ev.type === "error") emit("error", String(ev.message ?? "Codex báo lỗi"));
    else if (ev.type === "item.started" || ev.type === "item.completed") {
      const it = ev.item ?? {}, finished = ev.type === "item.completed";
      if (it.type === "agent_message" && finished) { emit("text", (sepNext ? "\n\n" : "") + String(it.text ?? "")); sepNext = true; }
      else if (it.type === "mcp_tool_call") {
        if (it.server === "ask") { hidden.add(it.id); return; }
        if (!finished) { sepNext = false; emit("tool_use", { id: it.id, name: it.tool, server: serverNames[it.server] ?? it.server, input: it.arguments }); }
        else {
          const failed = it.status === "failed" || !!it.error;
          const content = failed && it.error?.message ? [{ type: "text", text: String(it.error.message) }] : normalize(it.result?.content);
          emit("tool_result", { id: it.id, isError: failed, content: attachLocalImages(content) });
        }
      } else if (it.type === "command_execution") {   // không mong đợi (đã dặn không dùng shell), nhưng nếu có thì hiện cho người dùng thấy
        if (!finished) { sepNext = false; emit("tool_use", { id: it.id, name: "shell", input: { command: it.command } }); }
        else emit("tool_result", { id: it.id, isError: it.status === "failed" || (typeof it.exit_code === "number" && it.exit_code !== 0), content: [{ type: "text", text: String(it.aggregated_output || it.status || "") }] });
      } else if (it.type === "error" && finished && it.message) emit("notice", String(it.message).slice(0, 300));
    }
  };
  return { handle, threadId: () => threadId, finished: () => done };
}

/** Chạy một lượt chat qua Codex CLI (dùng tài khoản Codex đã đăng nhập trên máy). Trả về thread_id để nối tiếp. */
export function runCodex(
  prompt: string, sessionId: string | undefined, allowed: string[], emit: Emit, signal: AbortSignal, model: string,
  ask?: { run: Run; url: string }, serverList: McpServer[] = [], images: string[] = [],
): Promise<string | undefined> {
  mkdirSync(WORK, { recursive: true });
  const servers = serverList.filter(s => s.enabled);
  const { args, env } = codexArgs({ sessionId, model, servers, allowed, ask, images });
  const m = codexMapper(emit, Object.fromEntries(servers.map(s => [s.id, s.name])));

  return new Promise((resolve, reject) => {
    const p = spawn(CODEX_BIN, args, { cwd: WORK, stdio: ["pipe", "pipe", "pipe"], windowsHide: true, env: { ...process.env, ...env } });
    signal.addEventListener("abort", () => p.kill());
    p.stdin.end(prompt);

    let buf = "", err = "";
    p.stdout.setEncoding("utf8").on("data", (d: string) => {
      buf += d;
      let i: number;
      while ((i = buf.indexOf("\n")) >= 0) {
        const line = buf.slice(0, i).trim(); buf = buf.slice(i + 1);
        if (line.startsWith("{")) try { m.handle(JSON.parse(line)); } catch { /* dòng không phải JSON */ }
      }
    });
    p.stderr.setEncoding("utf8").on("data", d => { err += d; });
    p.on("error", e => reject(new Error((e as NodeJS.ErrnoException).code === "ENOENT" ? "Không tìm thấy lệnh codex trên máy chạy gateway. Cài Codex CLI hoặc đặt CODEX_BIN." : e.message)));
    p.on("close", code => {
      if (signal.aborted) return resolve(m.threadId() ?? sessionId);
      if (!m.finished() && code !== 0) return reject(new Error(err.trim().split("\n").filter(l => !/^\d{4}-\d\d-\d\dT/.test(l)).slice(-3).join(" ").slice(0, 400) || `codex thoát với mã ${code}`));
      resolve(m.threadId() ?? sessionId);
    });
  });
}
