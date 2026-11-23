import "./envInit.js";
import { serve } from "@hono/node-server";
import { serveStatic } from "@hono/node-server/serve-static";
import { readFileSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { homedir } from "node:os";
import { Hono } from "hono";
import { cors } from "hono/cors";
import { streamSSE } from "hono/streaming";
import { statusOf, tempClients } from "./mcp.js";
import { effortFor, engineFor, getEngine, getKey, getModel, getModels, modelFor, publicConfig, saveConfig, type McpServer } from "./config.js";
import { runChat } from "./chat.js";
import { friendly } from "./errors.js";
import { skillsNote } from "./skillsNote.js";
import { launcherRefs, runCliLocal, cliVersion } from "./cli.js";
import { runCodex, codexVersion } from "./codex.js";
import { ensureCodexModels } from "./codexmodels.js";
import { claudeStatus, machineCheck, startGitInstall, startInstall, startLogin } from "./claudeSetup.js";
import { codexSetupStatus, startCodexInstall, startCodexLogin } from "./codexSetup.js";
import { createEntry, moveEntry, pasteEntry, relPath, renameEntry, searchEntries, uploadTarget, createProject, openProject, locateFolder, deleteProject, deleteFolderProblem, folderStats, lockedFiles, getProject, importFiles, inside, listFiles, listProjects, updateProject, scopeOf, PROJECTS_ROOT } from "./projects.js";
import { openWithDialog, pickFiles, pickFolder, toRecycleBin } from "./pick.js";
import { planUsage, probeClaude } from "./planUsage.js";
import { toast } from "./toast.js";
import { cliList, startCliUpdate } from "./cliUpdates.js";
import { spawn } from "node:child_process";
import { createReadStream, createWriteStream, existsSync, rmSync, statSync, writeFileSync } from "node:fs";
import { pipeline } from "node:stream/promises";
import { Readable } from "node:stream";
import { resolve } from "node:path";
import { boardByToken, boardFor, runTool, USER } from "./coord.js";
import { Run, runByToken, runForAnswer } from "./ask.js";
import { AttachmentError, rebuildContent, splitContent, stage, type Staged, type UserImage } from "./attachments.js";
import { deleteConversation, getConversation, listConversations, ownsCliSession, putConversation, readImage, rememberCliSession, validFile, validId } from "./store.js";

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
// LiteBIM / LiteCAD chỉ có khi máy cài sản phẩm đó: hỏi launcher (/status) rồi tự thêm, trừ khi LOCAL_MCP đặt danh sách cố định.
const OPTIONAL_MCP: [string, string][] = [["litebim", "LiteBIM"], ["litecad", "LiteCAD"]];
let optCache: { at: number; keys: [string, string][] } = { at: 0, keys: [] };
async function installedOptional(): Promise<[string, string][]> {
  if (optCache.at > Date.now() - 30_000) return optCache.keys;
  let keys: [string, string][] = [];
  try {
    const r = await fetch(`${LOCAL_MCP_BASE}/status`, { signal: AbortSignal.timeout(2000) });
    const st: any = await r.json();
    keys = OPTIONAL_MCP.filter(([k]) => st?.[k]?.installed === true);
  } catch { /* launcher chưa chạy: chỉ dùng danh sách chuẩn */ }
  optCache = { at: Date.now(), keys };
  return keys;
}
async function localServers(): Promise<McpServer[]> {
  const fixed = (process.env.LOCAL_MCP ?? DEFAULT_LOCAL_MCP).split(",").map(s => s.trim()).filter(Boolean).map(entry => {
    const i = entry.indexOf(":");
    return [(i > 0 ? entry.slice(0, i) : entry).trim(), (i > 0 ? entry.slice(i + 1) : entry).trim()] as [string, string];
  });
  const all = process.env.LOCAL_MCP ? fixed : [...fixed, ...(await installedOptional()).filter(([k]) => !fixed.some(([f]) => f === k))];
  return all.map(([key, name]) => ({ id: key, name, enabled: true, transport: "http" as const, url: `${LOCAL_MCP_BASE}/${key}/mcp` }));
}
/** MCP của máy này, cộng với close() không-làm-gì (giữ cho khớp hình dạng dùng ở các route dưới). */
async function openMcp(): Promise<{ servers: McpServer[]; close: () => void }> { return { servers: await localServers(), close: () => {} }; }

const app = new Hono();
app.use("/api/*", cors({ origin: ORIGINS, credentials: true }));

const OWNER = "local";
// Mỗi yêu cầu nói nó thuộc dự án nào (?project=<id> hoặc body.project); không có thì là dự án đầu tiên.
const projectScope = (id: unknown) => scopeOf(typeof id === "string" ? id : undefined);
const NO_PROJECT = { error: "Không có dự án này (có thể đã bị xóa). Chọn dự án khác." };

// CLI/Codex chạy NGAY TRÊN MÁY NÀY (cùng máy với gateway), nên MCP `ask` gọi ngược về loopback, không cần địa chỉ công khai.
const ASK_URL = `http://127.0.0.1:${PORT}/internal/ask`;
const COORD_URL = `http://127.0.0.1:${PORT}/internal/coord`;

app.get("/api/health", async c => {
  const mcp = await openMcp();
  try {
    const list = await Promise.all(mcp.servers.map(async s => { const st = await statusOf(s); return { id: s.id, name: s.name, ok: st.ok, tools: st.tools.length, error: st.error }; }));
    const tools = list.reduce((n, x) => n + x.tools, 0);
    if (list.some(x => x.ok)) return c.json({ ok: true, tools, servers: list });
    return c.json({ ok: false, tools: 0, servers: list, error: `Không nối được MCP nào (${list.map(x => x.name).join(", ")}). Mở AutoCAD MCP Launcher và bật "Bật kết nối cho agent".` }, 503);
  } finally { mcp.close(); }
});

let skillCache: { at: number; list: { name: string; description: string; server: string }[] } | null = null;

app.get("/api/models", async c => {
  const engine = engineFor(c.req.query("engine"));
  if (engine === "codex") await ensureCodexModels();
  const list = getModels(engine);
  return c.json({ engine, models: list, default: list.find(m => m.id === getModel(engine))?.id ?? list[0].id });
});

// Các agent chọn được khi tạo phiên chat mới, kèm trạng thái cài/đăng nhập trên máy này.
app.get("/api/agents", async c => {
  const [cl, cx] = await Promise.all([claudeStatus(), codexSetupStatus()]);
  return c.json({
    default: getEngine(),
    agents: [
      { id: "cli", name: "Claude", detail: "Claude CLI", installed: cl.installed, loggedIn: cl.loggedIn, version: cl.version, installing: cl.installing, error: cl.installError, account: cl.email, needsGit: cl.needsGit, problem: cl.installProblem },
      { id: "codex", name: "Codex", detail: "Codex CLI", installed: cx.installed, loggedIn: cx.loggedIn, version: cx.version, installing: cx.installing, error: cx.installError, account: null },
      { id: "api", name: "Claude API", detail: "Anthropic API key", installed: true, loggedIn: !!getKey(), version: null, installing: false, error: null, account: null },
    ],
  });
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
// Thông báo Windows khi agent xong / cần trả lời. Chỉ khi trang được mở NGAY TRÊN máy này (localhost):
// mở qua tunnel từ máy khác thì thông báo sẽ hiện nhầm ở máy này, nên từ chối để web dùng thông báo của trình duyệt.
app.post("/api/notify", async c => {
  const host = (c.req.header("x-forwarded-host") ?? c.req.header("host") ?? "").replace(/:\d+$/, "").replace(/^\[|\]$/g, "");
  if (!["localhost", "127.0.0.1", "::1"].includes(host)) return c.json({ error: "Chỉ dùng khi mở CAD Studio trên chính máy này." }, 403);
  const b = await c.req.json().catch(() => ({}));
  const r = toast(String(b?.title ?? "CAD Studio"), String(b?.body ?? ""), String(b?.url ?? ""));
  return r.ok ? c.json({ ok: true }) : c.json({ error: r.error }, 501);
});
// Hạn mức gói tài khoản Claude/Codex (thanh "Đã sử dụng" ở đáy trang).
app.get("/api/plan-usage", async c => c.json(await planUsage()));
app.post("/api/plan-usage/refresh", async c => { await probeClaude(); return c.json(await planUsage()); });
app.get("/api/cli-updates", async c => c.json({ clis: await cliList(c.req.query("force") === "1") }));
app.post("/api/cli-updates/:id", async c => { const r = await startCliUpdate(c.req.param("id")); return r.error ? c.json(r, 400) : c.json({ ok: true }); });
app.get("/api/claude/status", async c => c.json(await claudeStatus()));
app.post("/api/claude/install", c => { const r = startInstall({ via: c.req.query("via") === "npm" ? "npm" : "script" }); return r.error ? c.json(r, 400) : c.json({ ok: true }); });
app.post("/api/claude/git", c => { const r = startGitInstall(); return r.error ? c.json(r, 400) : c.json({ ok: true, ...r }); });
// "Kiểm tra máy": điều kiện để Claude CLI chạy được (mạng, Claude CLI, Git Bash, PATH, npm, đăng nhập, hồ sơ).
app.get("/api/claude/doctor", async c => c.json({ checks: await machineCheck() }));
app.get("/api/codex/status", async c => c.json(await codexSetupStatus()));
app.post("/api/codex/install", c => { const r = startCodexInstall(); return r.error ? c.json(r, 500) : c.json({ ok: true }); });
app.post("/api/codex/login", c => { const r = startCodexLogin(); return r.error ? c.json(r, 400) : c.json({ ok: true }); });
app.post("/api/claude/login", c => { const r = startLogin(); return r.error ? c.json(r, 400) : c.json({ ok: true }); });

/** Skill hiện có (tool `skills` operation=list của các MCP), cache 60 giây. Rỗng khi tool skills không được phép. */
async function skillList(): Promise<{ name: string; description: string; server: string }[]> {
  if (ALLOWED.length && !ALLOWED.includes("skills")) return [];
  if (skillCache && skillCache.at > Date.now() - 60_000) return skillCache.list;
  const mcp = await openMcp();
  const list: { name: string; description: string; server: string }[] = [];
  const pool = tempClients(mcp.servers);
  try {
    await Promise.all(mcp.servers.map(async s => {
      try {
        const tools = (await pool.with(s.id, cl => cl.listTools())).tools;
        if (!tools.some(t => t.name === "skills")) return;
        const res: any = await pool.with(s.id, cl => cl.callTool({ name: "skills", arguments: { operation: "list" } }, undefined, { timeout: 20_000 }));
        const j = JSON.parse(res.content?.find((x: any) => x.type === "text")?.text ?? "{}");
        // Mọi MCP của launcher (AutoCAD, LiteBIM, LiteCAD) cùng trả MỘT bộ skill: chỉ giữ mỗi tên một lần.
        for (const x of Array.isArray(j.skills) ? j.skills : []) if (x?.name && !list.some(y => y.name === String(x.name))) list.push({ name: String(x.name), description: String(x.description ?? ""), server: s.name });
      } catch { /* server lỗi thì bỏ qua phần gợi ý của nó */ }
    }));
  } finally { await pool.close(); mcp.close(); }
  skillCache = { at: Date.now(), list };
  return list;
}
app.get("/api/skills", async c => c.json({ skills: await skillList() }));

app.get("/api/projects", c => c.json({ projects: listProjects() }));
app.post("/api/projects", async c => {
  const b = await c.req.json().catch(() => ({}));
  const r = createProject(b?.name, b?.dir);
  return "error" in r ? c.json(r, 400) : c.json(r);
});
// Mở một thư mục có sẵn làm dự án (đã là dự án thì trả dự án đó, không tạo trùng).
app.post("/api/projects/open", async c => {
  const b = await c.req.json().catch(() => ({}));
  const r = openProject(b?.dir);
  return "error" in r ? c.json(r, 400) : c.json(r);
});
// Kéo thả thư mục từ Explorer: trình duyệt chỉ cho biết TÊN thư mục, gateway tìm đường dẫn đầy đủ ở các chỗ quen thuộc.
app.post("/api/projects/locate", async c => {
  const b = await c.req.json().catch(() => ({}));
  return c.json({ dirs: locateFolder(b?.name) });
});
app.patch("/api/projects/:id", async c => {
  const b = await c.req.json().catch(() => ({}));
  const r = updateProject(c.req.param("id"), { name: b?.name, pinned: b?.pinned, shell: b?.shell });
  return "error" in r ? c.json(r, 400) : c.json(r);
});
// Phiên chat đang chạy theo dự án (để không xóa thư mục khi agent còn đang làm trong đó).
const activeChats = new Map<string, number>();
/** Lý do chưa được xóa thư mục vì dự án đang bận (phiên đang chạy / khoá điều phối); null = rảnh. */
function busyProblem(p: { id: string; dir: string | null }): string | null {
  if ((activeChats.get(p.id) ?? 0) > 0) return "Dự án đang có phiên chat chạy; dừng phiên đó rồi xóa lại.";
  if (p.dir && existsSync(p.dir)) {
    try {
      const s = boardFor(p.dir).snapshot();
      if (s.running.length) return "Dự án đang có agent chạy (bảng điều phối); đợi xong hoặc dừng rồi xóa lại.";
      if (s.locks.length) return `Dự án đang có ${s.locks.length} khoá điều phối (${s.locks.map(l => l.target).slice(0, 3).join(", ")}); gỡ khoá ở tab Khoá rồi xóa lại.`;
    } catch { /* không đọc được bảng điều phối: coi như rảnh */ }
  }
  return null;
}

// Thông tin cho hộp xác nhận xóa: thư mục, số file, dung lượng, và có được xóa thư mục không (lý do nếu không).
app.get("/api/projects/:id/delete-info", c => {
  const all = listProjects();
  const p = all.find(x => x.id === c.req.param("id"));
  if (!p) return c.json({ error: "Không có dự án này." }, 404);
  const exists = !!p.dir && existsSync(p.dir);
  return c.json({ dir: p.dir, exists, ...(exists ? folderStats(p.dir!) : { files: 0, bytes: 0, capped: false }),
    folderProblem: deleteFolderProblem(p, all) ?? busyProblem(p) });
});

app.delete("/api/projects/:id", async c => {
  const id = c.req.param("id");
  const all = listProjects();
  const p = all.find(x => x.id === id);
  if (!p) return c.json({ error: "Không có dự án này." }, 404);
  if (all.length === 1) return c.json({ error: "Phải còn ít nhất một dự án." }, 400);
  const deleteFolder = c.req.query("deleteFolder") === "1" || c.req.query("deleteFolder") === "true";
  let recycled = false;
  if (deleteFolder && p.dir && existsSync(p.dir)) {
    const problem = deleteFolderProblem(p, all) ?? busyProblem(p);
    if (problem) return c.json({ error: problem }, 409);
    const locked = lockedFiles(p.dir);
    if (locked.length) return c.json({ error: `Có file đang được chương trình khác mở, chưa xóa được: ${locked.map(f => relative(p.dir!, f)).join(", ")}. Đóng các file đó (ví dụ bản vẽ trong AutoCAD) rồi thử lại.` }, 409);
    try { await toRecycleBin(p.dir, true); recycled = true; }
    catch (e: any) { return c.json({ error: `Không chuyển được thư mục vào Thùng rác: ${String(e?.message ?? e).split(/\r?\n/)[0]}. Dự án vẫn còn nguyên.` }, 500); }
  }
  const r = deleteProject(id);
  if (r === "last") return c.json({ error: "Phải còn ít nhất một dự án." }, 400);
  return r ? c.json({ ok: true, recycled, dir: p.dir }) : c.json({ error: "Không có dự án này." }, 404);
});

// Hộp chọn thư mục/file của Windows (mở trên máy này). Hủy thì trả null/rỗng.
// Thư mục mở sẵn: thư mục cha của dự án mới nhất (thường các dự án nằm cạnh nhau), không có thì Documents.
const pickStart = () => {
  const last = [...listProjects()].filter(p => p.dir && existsSync(p.dir)).sort((a, b) => b.createdAt - a.createdAt)[0];
  return last?.dir ? dirname(last.dir) : join(homedir(), "Documents");
};
app.post("/api/pick/folder", async c => {
  const b = await c.req.json().catch(() => ({}));
  const title = b?.purpose === "open" ? "Mở dự án có sẵn: chọn thư mục dự án" : "Chọn thư mục lưu dự án";
  try { return c.json({ path: await pickFolder(title, pickStart()) }); }
  catch (e: any) { return c.json({ error: `Không mở được hộp chọn thư mục: ${e?.message ?? e}` }, 500); }
});
app.post("/api/pick/files", async c => {
  try { return c.json({ paths: await pickFiles("Chọn file hồ sơ đưa vào dự án", pickStart()) }); }
  catch (e: any) { return c.json({ error: `Không mở được hộp chọn file: ${e?.message ?? e}` }, 500); }
});
const projOr404 = (c: any) => getProject(c.req.param("id"));
app.get("/api/projects/:id/files", c => {
  const p = projOr404(c);
  if (!p) return c.json(NO_PROJECT, 404);
  if (!p.dir) return c.json({ entries: [], dir: null });
  const list = listFiles(p, c.req.query("path") ?? "");
  return list ? c.json({ entries: list, dir: p.dir }) : c.json({ error: "Không có thư mục này trong dự án." }, 404);
});
app.post("/api/projects/:id/import", async c => {
  const p = projOr404(c);
  if (!p) return c.json(NO_PROJECT, 404);
  const b = await c.req.json().catch(() => ({}));
  const r = importFiles(p, b?.paths);
  return "error" in r ? c.json(r, 400) : c.json(r);
});
app.post("/api/projects/:id/new", async c => {
  const p = projOr404(c);
  if (!p?.dir) return c.json(NO_PROJECT, 404);
  const b = await c.req.json().catch(() => ({}));
  const r = createEntry(p, b?.parent, b?.name, b?.kind === "dir" ? "dir" : "file");
  return "error" in r ? c.json(r, 400) : c.json(r);
});
app.post("/api/projects/:id/trash", async c => {
  const p = projOr404(c);
  const b = await c.req.json().catch(() => ({}));
  const rel = typeof b?.path === "string" ? b.path : "";
  const full = p && rel ? inside(p, rel) : null;   // không bao giờ xóa chính thư mục dự án
  if (!full || full === resolve(p!.dir!) || !existsSync(full)) return c.json({ error: "Không có file/thư mục này trong dự án." }, 404);
  try { await toRecycleBin(full, statSync(full).isDirectory()); return c.json({ ok: true }); }
  catch (e: any) { return c.json({ error: `Không xóa được (file có thể đang mở trong AutoCAD/Excel): ${String(e?.message ?? e).split("\n")[0].trim()}` }, 500); }
});
// Thao tác file ở cột phải: đổi tên, dán (chép), tìm theo tên, mở bằng ứng dụng mặc định.
const fileOp = (fn: (p: NonNullable<ReturnType<typeof getProject>>, b: any) => object) => async (c: any) => {
  const p = projOr404(c);
  if (!p?.dir) return c.json(NO_PROJECT, 404);
  const b = await c.req.json().catch(() => ({}));
  try { const r: any = fn(p, b); return "error" in r ? c.json(r, 400) : c.json(r); }
  catch (e: any) { return c.json({ error: `Không thực hiện được: ${String(e?.message ?? e).split("\n")[0]}` }, 500); }
};
app.post("/api/projects/:id/rename", fileOp((p, b) => renameEntry(p, b?.path, b?.name)));
app.post("/api/projects/:id/paste", fileOp((p, b) => pasteEntry(p, b?.src, b?.parent)));
app.post("/api/projects/:id/move", fileOp((p, b) => moveEntry(p, b?.src, b?.parent)));
// Kéo thả file từ Windows vào cột file: thân yêu cầu là nội dung file, ghi thẳng xuống đĩa (không đọc hết vào bộ nhớ).
app.post("/api/projects/:id/upload", async c => {
  const p = projOr404(c);
  if (!p?.dir) return c.json(NO_PROJECT, 404);
  const to = uploadTarget(p, c.req.query("parent") ?? "", c.req.query("rel") ?? "");
  if (!to) return c.json({ error: "Tên file không hợp lệ." }, 400);
  if (!c.req.raw.body) { writeFileSync(to, ""); return c.json({ path: relPath(p, to) }); }
  try {
    await pipeline(Readable.fromWeb(c.req.raw.body as any), createWriteStream(to, { flags: "wx" }));
    return c.json({ path: relPath(p, to) });
  } catch (e: any) {
    rmSync(to, { force: true });
    return c.json({ error: `Không chép được file: ${String(e?.message ?? e).split("\n")[0]}` }, 500);
  }
});
app.post("/api/projects/:id/search", fileOp((p, b) => { const r = searchEntries(p, b?.path, b?.q); return Array.isArray(r) ? { entries: r } : r; }));
app.post("/api/projects/:id/launch", fileOp((p, b) => {
  const full = inside(p, typeof b?.path === "string" ? b.path : "");
  if (!full || !existsSync(full)) return { error: "Không có file/thư mục này trong dự án." };
  if (b?.with === "choose") {
    // Hộp "Mở bằng" của Windows: người dùng tự chọn app, có thể tick "Luôn dùng ứng dụng này".
    void openWithDialog(full).catch(e => console.error("open with:", e?.message ?? e));
  } else {
    spawn("explorer.exe", [full], { detached: true, stdio: "ignore" }).unref();   // ứng dụng mặc định (DWG -> AutoCAD, XLSX -> Excel…)
  }
  return { ok: true };
}));
app.post("/api/projects/:id/reveal", async c => {
  const p = projOr404(c);
  const b = await c.req.json().catch(() => ({}));
  const full = p ? inside(p, typeof b?.path === "string" ? b.path : "") : null;
  if (!full || !existsSync(full)) return c.json({ error: "Không có file/thư mục này trong dự án." }, 404);
  spawn("explorer.exe", statSync(full).isDirectory() ? [full] : [`/select,${full}`], { detached: true, stdio: "ignore" }).unref();
  return c.json({ ok: true });
});
const RAW_TYPES: Record<string, string> = { png: "image/png", jpg: "image/jpeg", jpeg: "image/jpeg", gif: "image/gif", webp: "image/webp", svg: "image/svg+xml", pdf: "application/pdf", txt: "text/plain; charset=utf-8", md: "text/plain; charset=utf-8", csv: "text/plain; charset=utf-8", json: "text/plain; charset=utf-8" };
app.get("/api/projects/:id/raw", c => {
  const p = projOr404(c);
  const full = p ? inside(p, c.req.query("path") ?? "") : null;
  if (!full || !existsSync(full) || !statSync(full).isFile()) return c.json({ error: "Không có file này trong dự án." }, 404);
  const type = RAW_TYPES[full.split(".").pop()!.toLowerCase()] ?? "application/octet-stream";
  // SVG có thể chứa script: chỉ cho xem như ảnh tĩnh, không chạy được gì.
  return new Response(Readable.toWeb(createReadStream(full)) as any, { headers: { "Content-Type": type, "Content-Security-Policy": "sandbox; default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'", "X-Content-Type-Options": "nosniff" } });
});

app.use("/api/conversations/*", async (c, next) => { if (!projectScope(c.req.query("project"))) return c.json(NO_PROJECT, 404); await next(); });
app.get("/api/conversations", c => {
  const sc = projectScope(c.req.query("project"));
  return sc ? c.json({ conversations: listConversations(sc) }) : c.json(NO_PROJECT, 404);
});
app.get("/api/conversations/:id", c => {
  const id = c.req.param("id");
  const conv = validId(id) ? getConversation(projectScope(c.req.query("project"))!, id) : null;
  return conv ? c.json(conv) : c.json({ error: "Không tìm thấy cuộc trò chuyện." }, 404);
});
app.put("/api/conversations/:id", async c => {
  const id = c.req.param("id");
  if (!validId(id)) return c.json({ error: "id không hợp lệ" }, 400);
  const b = await c.req.json().catch(() => null);
  if (!b || typeof b !== "object") return c.json({ error: "Dữ liệu không hợp lệ" }, 400);
  const r = putConversation(projectScope(c.req.query("project"))!, id, b);
  return c.json({ id: r.id, title: r.title, updatedAt: r.updatedAt });
});
app.delete("/api/conversations/:id", c => {
  const id = c.req.param("id");
  if (!validId(id)) return c.json({ error: "id không hợp lệ" }, 400);
  deleteConversation(projectScope(c.req.query("project"))!, id);
  return c.json({ ok: true });
});
app.get("/api/files/:name", c => {
  const name = c.req.param("name");
  const sc = projectScope(c.req.query("project"));
  const f = sc && validFile(name) ? readImage(sc, name) : null;
  return f ? new Response(f.data, { headers: { "Content-Type": f.mime, "Cache-Control": "private, max-age=31536000, immutable" } }) : c.json({ error: "Không có file." }, 404);
});

app.post("/api/chat", async c => {
  const body = await c.req.json().catch(() => ({}));
  const engine = engineFor(body.engine);   // engine của phiên (chọn lúc tạo phiên), không có thì theo Cài đặt
  if (engine === "api" && !getKey()) return c.json({ error: "Chưa có API key. Vào tab Cài đặt để nhập, hoặc chọn agent khác cho phiên mới." }, 503);
  if (!Array.isArray(body.messages) || !body.messages.length) return c.json({ error: "thiếu messages" }, 400);
  const project = getProject(typeof body.project === "string" ? body.project : undefined);
  const SCOPE = projectScope(project?.id);
  if (!project || !SCOPE) return c.json(NO_PROJECT, 404);
  const workDir = project.dir ?? undefined;
  const mcp = await openMcp();
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
  // Danh sách skill + lời dặn nạp skill trước khi làm, cho mọi engine (lỗi thì bỏ qua, không chặn lượt chat).
  const note = skillsNote(await skillList().catch(() => []));
  return streamSSE(c, async s => {
    let staged: Staged | undefined;
    activeChats.set(project.id, (activeChats.get(project.id) ?? 0) + 1);
    const ac = new AbortController();
    s.onAbort(() => ac.abort());
    const emit = (event: string, data: unknown) => s.writeSSE({ event, data: JSON.stringify(data) });
    const run = new Run(OWNER, emit);
    let board: ReturnType<typeof boardFor> | undefined, owner = "", coordToken: string | undefined;
    let coord: { url: string; token: string; prompt: string } | undefined;
    try {
      if (engine === "codex") await ensureCodexModels();   // model Codex chọn cho phiên phải nằm trong danh mục
      if (engine === "cli" || engine === "codex") {
        staged = stage(userImages);
        const prompt = userText || (userImages.length ? "Hãy xem ảnh đính kèm." : "");
        if (!prompt) throw new Error("thiếu nội dung tin nhắn");
        const tag = engine === "codex" ? "codex:" : "";
        const asked = typeof body.sessionId === "string" ? body.sessionId : undefined;
        const resume = asked && ownsCliSession(SCOPE, tag + asked) ? asked : undefined;
        if (asked && !resume) await emit("notice", "Không nối lại được phiên trước đó của cuộc trò chuyện này, đã bắt đầu phiên mới.");
        const ask = { run, url: ASK_URL };
        // Bảng điều phối: chỉ khi dự án có thư mục và web gửi id phiên chat. Khoá của phiên được gia hạn tới khi tiến trình đóng.
        const convId = typeof body.conv === "string" && validId(body.conv) ? body.conv : undefined;
        if (project.dir && convId) {
          try {
            board = boardFor(project.dir); owner = convId;
            const label = (typeof body.title === "string" && body.title.trim() ? body.title.trim() : "Phiên chat").slice(0, 40);
            coordToken = board.begin(convId, { label, engine: engine === "codex" ? "codex" : "claude" });
            coord = { url: COORD_URL, token: coordToken, prompt: board.promptBlock(convId) };
          } catch (e) { console.error("coord:", (e as Error)?.message ?? e); }
        }
        const sessionId = engine === "codex"
          ? await runCodex(prompt, resume, ALLOWED, emit, ac.signal, modelFor(body.model, engine), ask, routed, staged?.files, workDir, effortFor(body.effort), coord, note)
          : await runCliLocal({ prompt, sessionId: resume, allowed: ALLOWED, emit, signal: ac.signal, model: modelFor(body.model, engine), ask, serverList: routed, att: staged, project: project.dir ? { name: project.name, dir: project.dir, shell: !!project.shell } : undefined, effort: effortFor(body.effort), coord, refs: await launcherRefs(LOCAL_MCP_BASE), extraSystem: note });
        if (sessionId) rememberCliSession(SCOPE, tag + sessionId);
        await emit("done", { messages: [], sessionId });
      } else {
        const messages = await runChat(body.messages, (name: string) => ALLOWED.length === 0 || ALLOWED.includes(name), emit, ac.signal, modelFor(body.model, engine), run, routed, note);
        await emit("done", { messages });
      }
    } catch (e) {
      if (!ac.signal.aborted) await emit("error", friendly(e));
    } finally {
      run.close(); mcp.close(); staged?.cleanup();
      activeChats.set(project.id, Math.max(0, (activeChats.get(project.id) ?? 1) - 1));
      if (board) board.end(owner, coordToken, ac.signal.aborted ? "người dùng dừng lượt" : "phiên kết thúc lượt");
    }
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

// Bảng điều phối agent (.cadstudio/coord.json). Web đọc bằng poll; người dùng gửi tin to:* và thu hồi khoá.
const coordBoard = (c: any, id: unknown) => { const p = getProject(typeof id === "string" ? id : undefined); return p?.dir ? boardFor(p.dir) : null; };
app.get("/api/coord", c => {
  const b = coordBoard(c, c.req.query("project"));
  return b ? c.json(b.snapshot()) : c.json({ agents: {}, locks: [], running: [], log: [], now: new Date().toISOString() });
});
app.post("/api/coord/post", async c => {
  const body = await c.req.json().catch(() => ({}));
  const b = coordBoard(c, body?.project);
  if (!b) return c.json(NO_PROJECT, 404);
  const r = b.post(USER, { to: "*", kind: "note", text: body?.text });
  return "error" in r ? c.json(r, 400) : c.json(r);
});
app.post("/api/coord/revoke", async c => {
  const body = await c.req.json().catch(() => ({}));
  const b = coordBoard(c, body?.project);
  if (!b) return c.json(NO_PROJECT, 404);
  const r = b.release(USER, { lock_id: body?.lock_id }, true);
  return "error" in r ? c.json(r, 404) : c.json(r);
});
// Cho giai đoạn 2 (launcher hỏi trước tool ghi AutoCAD): target có đang bị phiên KHÁC khoá ghi không.
app.get("/api/coord/check", c => {
  const b = coordBoard(c, c.req.query("project"));
  if (!b) return c.json(NO_PROJECT, 404);
  const session = c.req.query("session") ?? "", target = c.req.query("target") ?? "";
  const r = b.claimable(session, target);
  return "error" in r ? c.json(r, 400) : c.json(r);
});
// Gọi từ coord-mcp.mjs (con của Claude CLI/Codex), xác thực bằng token riêng của lượt chat.
app.post("/internal/coord", async c => {
  const hit = boardByToken(c.req.header("x-coord-token"));
  if (!hit) return c.json({ error: "Token không hợp lệ hoặc lượt chat đã kết thúc." }, 401);
  const b = await c.req.json().catch(() => null);
  return c.json(runTool(hit.board, hit.owner, String(b?.tool ?? ""), b?.args));
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
// Gateway vừa khởi động: không phiên nào còn chạy, dọn khoá mồ côi của mọi dự án có thư mục.
for (const p of listProjects()) if (p.dir && existsSync(p.dir)) { try { boardFor(p.dir); } catch (e) { console.error("coord:", (e as Error)?.message ?? e); } }
let listenTries = 0;
server.on("error", (e: NodeJS.ErrnoException) => {
  if (e.code === "EADDRINUSE" && listenTries++ < 40) { setTimeout(() => server.listen(PORT, HOST), 500); return; }
  console.error(e.code === "EADDRINUSE" ? `Cổng ${PORT} đang bị chương trình khác giữ.` : e); process.exit(1);
});

process.on("unhandledRejection", e => console.error("unhandledRejection:", e));
for (const sig of ["SIGINT", "SIGTERM"] as const) process.on(sig, () => process.exit(0));
