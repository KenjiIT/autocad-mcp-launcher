import { spawn, execFile } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { homedir, tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { ASK_DESCRIPTION, ASK_SCHEMA, type Run } from "./ask.js";
import { getModel, type McpServer } from "./config.js";
import type { Emit } from "./chat.js";
import { usageOf } from "./usage.js";
import { attachLocalImages, roots } from "./localImages.js";
import { claudeBin } from "./claudeSetup.js";
import { recordClaudeRate } from "./planUsage.js";
import { COORD_TOOLS, COORD_TOOL_NAMES } from "./coord.js";

// Bạn đang chạy trong CAD Studio (web), KHÔNG phải Claude Code: người dùng không gõ được /permissions hay lệnh "/" nào.
const SHELL_OFF = "Bạn đang chạy trong CAD Studio, không có công cụ chạy lệnh (Bash/PowerShell/Python). " +
  "Nếu việc cần chạy script hay lệnh, ĐỪNG bảo người dùng gõ /permissions hay lệnh / nào (CAD Studio không có). " +
  "Hãy nói: chuột phải vào dự án ở cột trái > bật \"Cho agent chạy lệnh\", rồi nhắn lại để bạn làm tiếp; hoặc làm bằng tool MCP nếu được. " +
  "Chạy lệnh chỉ có khi đang mở một dự án có thư mục.";
const SHELL_ON = "Dự án này đã bật \"Cho agent chạy lệnh\": bạn có công cụ Bash, thư mục làm việc là thư mục dự án. " +
  "Chỉ đọc/ghi trong thư mục dự án; dữ liệu nằm ngoài thì nhờ người dùng chép vào dự án. Không cài phần mềm, không xóa file ngoài dự án.";
const SYSTEM = process.env.CHAT_SYSTEM ??
  "Khi cần trình bày bố cục, mặt bằng hay sơ đồ không gian thì vẽ thành hình SVG (lưu file .svg trong thư mục dự án và nhắc đường dẫn, hoặc đặt nguyên SVG trong khối ```svg), không vẽ bằng ký tự/ASCII. " +
  "Bạn là trợ lý điều khiển AutoCAD qua các tool MCP. Trả lời bằng tiếng Việt, ngắn gọn. " +
  "Trước khi sửa bản vẽ hãy đọc/đo để chắc chắn, và nói rõ bạn đã thay đổi gì. " +
  "Khi một tool chỉ trả đường dẫn file ảnh (\"inline\": false), hãy dùng công cụ Read mở file đó để xem ảnh trước khi mô tả. " +
  "Khi kết quả tool quá dài, CLI tự lưu vào file tool-results và đưa bạn đường dẫn: dùng Read đọc file đó (đã được phép sẵn, có thể đọc từng đoạn bằng offset/limit); đừng bảo người dùng cấp quyền thư mục. " +
  "Khi cần người dùng chọn giữa vài phương án rời rạc (xác nhận, chọn hướng, có/không), hãy gọi tool mcp__ask__ask_user để hiện bảng lựa chọn, đừng liệt kê bằng chữ rồi chờ họ gõ.";
const WORK = join(tmpdir(), "cad-web-cli");
const ASK_MCP = fileURLToPath(new URL("./ask-mcp.mjs", import.meta.url));
export const COORD_MCP = fileURLToPath(new URL("./coord-mcp.mjs", import.meta.url));
/** MCP `coord` của lượt (bảng điều phối dự án): url gọi ngược gateway, token của lượt, khối tình trạng chèn vào system prompt. */
export type CoordTurn = { url: string; token: string; prompt: string };

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
  coord?: CoordTurn;
  extraSystem?: string;                     // khối dặn thêm (danh sách skill…), nối cuối system prompt
  refs?: RefDoc[];                          // tài liệu API LiteBIM/LiteCAD launcher đã lưu (chỉ Read)
  effort?: string;                          // --effort của Claude CLI (low|medium|high|xhigh|max)  // dự án: CLI chạy trong thư mục này và được đọc file trong đó
};

const slash = (p: string) => p.replace(/\\/g, "/").replace(/\/+$/, "");

/** Tài liệu API (kết quả get_reference) launcher lưu ở launcher/state/<sản phẩm>/reference/. */
export type RefDoc = { id: string; title: string; path: string; dir: string; version?: string | null; fetchedAt?: string | null };

/** Đọc /status của launcher, lấy các tài liệu đã lưu. Lỗi / launcher cũ thì []. Tách parse ra để kiểm thử. */
export function parseRefs(status: any): RefDoc[] {
  const ref = status?.reference;
  if (!ref || typeof ref !== "object") return [];
  const TITLE: Record<string, string> = { litebim: "LiteBIM", litecad: "LiteCAD" };
  return Object.entries(ref).flatMap(([id, v]: [string, any]) => v?.available && typeof v.path === "string" && typeof v.dir === "string"
    ? [{ id, title: TITLE[id] ?? id, path: v.path, dir: v.dir, version: v.version ?? null, fetchedAt: v.fetched_at ?? null }] : []);
}
let refCache: { at: number; list: RefDoc[] } | null = null;
export async function launcherRefs(base: string): Promise<RefDoc[]> {
  if (refCache && Date.now() - refCache.at < 60_000) return refCache.list;
  try {
    const r = await fetch(`${base}/status`, { signal: AbortSignal.timeout(3000) });
    refCache = { at: Date.now(), list: r.ok ? parseRefs(await r.json()) : [] };
  } catch { refCache = { at: Date.now(), list: [] }; }
  return refCache.list;
}

/** Dòng system prompt chỉ cho agent đọc tài liệu đã lưu thay vì gọi get_reference. */
export function refPrompt(refs: RefDoc[]): string {
  return refs.map(r => `Tài liệu API ${r.title}${r.version ? ` (phiên bản ${r.version})` : ""} đã lưu sẵn ở file ${r.path}. ` +
    `Muốn biết API/cách viết script ${r.title} thì dùng Read đọc file đó (file dài: đọc từng đoạn bằng offset/limit, hoặc Grep tìm tên lớp/hàm trong thư mục ${r.dir}) ` +
    `thay vì gọi tool get_reference.`).join("\n");
}

/** Thư mục cấu hình mà tiến trình `claude` dùng: CLAUDE_CONFIG_DIR nếu có, mặc định ~/.claude. */
export function claudeConfigDir(env: NodeJS.ProcessEnv = process.env, home = homedir()): string {
  return slash(env.CLAUDE_CONFIG_DIR?.trim() || join(home, ".claude"));
}

/** Tên thư mục CLI đặt cho một cwd dưới <config>/projects/ (mọi ký tự không phải chữ/số thành "-"). */
export const cliProjectSlug = (cwd: string) => cwd.replace(/[^a-zA-Z0-9]/g, "-");

/**
 * --tools, --allowedTools, --disallowedTools, --add-dir cho một lượt chat (-p không hỏi quyền nên chỉ những gì liệt kê ở đây mới chạy được).
 * Read luôn bật, nhưng chỉ trong: thư mục ảnh, thư mục đính kèm, thư mục dự án, và thư mục tool-results của chính CLI
 * (nơi CLI tự lưu kết quả tool MCP quá dài rồi bảo agent đọc lại: <config>/projects/<slug cwd>/<phiên>/tool-results/).
 * Thư mục cấu hình của CLI được bảo vệ riêng: rule Read(...) thôi không đủ (đã thử thật, vẫn bị từ chối), phải --add-dir.
 * Nên add-dir hẹp nhất có thể (chỉ thư mục của cwd này) và chặn đọc transcript *.jsonl trong đó.
 */
export function cliPermissions(o: {
  servers: Pick<McpServer, "id">[]; allowed: string[]; ask?: boolean; coord?: boolean; imageRoots: string[]; attDir?: string; refDirs?: string[];
  project?: { dir: string; shell?: boolean }; cwd: string; configDir?: string;
}): { tools: string; allow: string[]; deny: string[]; addDirs: string[] } {
  const allow = o.servers.flatMap(s => o.allowed.length ? o.allowed.map(n => `mcp__${s.id}__${n}`) : [`mcp__${s.id}`]);
  if (o.ask) allow.push("mcp__ask__ask_user");
  if (o.coord) for (const n of COORD_TOOL_NAMES) allow.push(`mcp__coord__${n}`);
  for (const r of o.imageRoots) allow.push(`Read(${slash(r)}/**)`);
  if (o.attDir) allow.push(`Read(${slash(o.attDir)}/**)`);   // đúng thư mục tạm của lượt này, không rộng hơn
  const slug = cliProjectSlug(o.cwd);
  // CLI cắt slug dài (>200 ký tự) và thêm hash: khi đó lùi về cả projects/, rule Read vẫn chỉ cho tool-results
  const results = `${o.configDir ? slash(o.configDir) : claudeConfigDir()}/projects${slug.length <= 200 ? `/${slug}` : ""}`;
  allow.push(`Read(${results}/**/tool-results/**)`);   // chỉ Read, chỉ tool-results
  const deny = ["Read", "Glob", "Grep"].flatMap(t => [`${t}(${results}/*.jsonl)`, `${t}(${results}/**/*.jsonl)`]);   // transcript hội thoại
  const proj = o.project;
  if (proj) for (const t of ["Read", "Glob", "Grep", "Write", "Edit"]) allow.push(`${t}(${slash(proj.dir)}/**)`);
  if (proj?.shell) allow.push("Bash");   // người dùng đã bật "Cho agent chạy lệnh" cho dự án này
  // Tài liệu API do launcher lưu: chỉ Read/Grep (Glob để thấy file chủ đề), thêm --add-dir để CLI cho đọc ngoài cwd.
  for (const d of o.refDirs ?? []) for (const t of ["Read", "Grep", "Glob"]) allow.push(`${t}(${slash(d)}/**)`);
  const tools = proj ? `Read,Glob,Grep,Write,Edit${proj.shell ? ",Bash" : ""}` : o.refDirs?.length ? "Read,Glob,Grep" : "Read";   // không dự án: chỉ đọc (giới hạn như trên)
  return { tools, allow, deny, addDirs: [results, ...(o.refDirs ?? []).map(slash)] };
}

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
  if (a.coord) mcpServers.coord = { type: "stdio", command: process.execPath, args: [COORD_MCP], env: {
    COORD_URL: a.coord.url, COORD_TOKEN: a.coord.token, COORD_TOOLS: JSON.stringify(COORD_TOOLS) } };
  writeFileSync(mcpFile, JSON.stringify({ mcpServers }), { mode: 0o600 });  // có thể chứa token nên chỉ chủ file đọc được
  const names = nameMap(servers);
  const proj = a.project;
  const cwd = proj?.dir ?? WORK;
  const { tools, allow, deny, addDirs } = cliPermissions({ servers, allowed, ask: !!ask, coord: !!a.coord, refDirs: a.refs?.map(r => r.dir), imageRoots: roots(), attDir: att?.dir, project: proj, cwd });
  if (att) prompt += `\n\n[Người dùng đã đính kèm ${att.files.length} ảnh. Hãy dùng công cụ Read mở từng file dưới đây để xem trước khi trả lời:\n${att.files.map(f => `- ${f}`).join("\n")}]`;

  const args = [
    "-p", "--output-format", "stream-json", "--verbose", "--include-partial-messages",
    "--mcp-config", mcpFile, "--strict-mcp-config",
    "--tools", tools,
    "--allowedTools", allow.join(","),
    "--disallowedTools", deny.join(","),
    ...addDirs.flatMap(d => ["--add-dir", d]),
    "--disable-slash-commands",
    "--append-system-prompt", proj ? `${SYSTEM}
Đang làm việc trong dự án "${proj.name}", thư mục ${proj.dir}. Hồ sơ, bản vẽ tham chiếu của dự án nằm trong thư mục này; dùng Glob/Grep/Read để tìm và đọc khi cần. File bạn tạo ra (báo cáo, bảng tính, DXF, ảnh xuất…) phải lưu trong thư mục này, không lưu nơi khác.
${proj.shell ? SHELL_ON : SHELL_OFF}${a.coord ? `
${a.coord.prompt}` : ""}${a.refs?.length ? `
${refPrompt(a.refs)}` : ""}${a.extraSystem ? `
${a.extraSystem}` : ""}` : `${SYSTEM}
${SHELL_OFF}${a.refs?.length ? `
${refPrompt(a.refs)}` : ""}${a.extraSystem ? `
${a.extraSystem}` : ""}`,
    "--model", model,
    ...(a.effort ? ["--effort", a.effort] : []),
    ...(sessionId ? ["--resume", sessionId] : []),
  ];

  return new Promise((resolve, reject) => {
    // MCP_TOOL_TIMEOUT: tool ask_user có thể chờ người dùng rất lâu, mặc định của CLI sẽ cắt ngang.
    const p = spawn(claudeBin(), args, { cwd, stdio: ["pipe", "pipe", "pipe"], windowsHide: true, env: { ...process.env, MCP_TOOL_TIMEOUT: "1800000" } });
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
