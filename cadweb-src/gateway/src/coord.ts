import { randomBytes } from "node:crypto";
import { readFileSync, rmSync, statSync } from "node:fs";
import { writeFile, rename, appendFile } from "node:fs/promises";
import { isAbsolute, join, relative, resolve } from "node:path";
import { localDir } from "./store.js";

// Bảng điều phối nhiều agent trong cùng một dự án (giai đoạn 1 của de-xuat-phoi-hop-agent.md).
//   <dự án>/.cadstudio/coord.json      trạng thái: ai đang làm gì, khoá nào đang giữ
//   <dự án>/.cadstudio/coord-log.jsonl nhật ký tin nhắn (chỉ thêm)
// CHỈ gateway ghi hai file này (một tiến trình): trạng thái giữ trong bộ nhớ, mọi thay đổi xếp vào một hàng đợi ghi của
// từng dự án; mỗi lần ghi coord.json là ghi file tạm rồi rename (atomic), nên đọc giữa chừng không bao giờ thấy file dở.
// Agent thao tác qua MCP `coord` (coord-mcp.mjs) gọi POST /internal/coord kèm token của lượt chat.

export type Agent = { label: string; engine: string; task: string; status: "working" | "idle"; heartbeat: string };
export type Lock = { id: string; kind: "file" | "drawing"; target: string; mode: "write" | "read"; owner: string; reason: string; since: string; expires: string };
export type Msg = { t: string; from: string; to: string; kind: "note" | "handoff" | "question" | "lock" | "system"; text: string; refs?: string[] };
type State = { version: 1; seq: number; agents: Record<string, Agent>; locks: Lock[] };

export const USER = "user";                 // tin người dùng gửi từ tab Trao đổi
export const SYSTEM = "system";
const DEFAULT_TTL_MIN = 10, MAX_TTL_MIN = 60;
const RENEW_MS = Number(process.env.COORD_RENEW_MS ?? 30_000);   // gia hạn khoá của phiên đang chạy
const LOG_MAX_BYTES = 512 * 1024, LOG_KEEP = 1000;
const AGENT_KEEP_MS = 7 * 86_400_000;      // phiên rảnh quá 7 ngày thì bỏ khỏi bảng

let clock = () => Date.now();
/** Chỉ cho test: đổi đồng hồ. */
export const _setClock = (fn: () => number) => { clock = fn; };
const iso = (ms = clock()) => new Date(ms).toISOString();
const hhmm = (s: string) => { const d = new Date(s); return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`; };
const str = (v: unknown, max: number) => (typeof v === "string" ? v.trim().replace(/\s+/g, " ").slice(0, max) : "");

/**
 * Chuẩn hoá target: `file:<đường dẫn tương đối dự án>` (dấu /, bỏ ./), `dwg:<đường dẫn đầy đủ>` (dấu /).
 * Đường dẫn tuyệt đối nằm trong dự án viết ở dạng file: thì đổi về tương đối. So khớp không phân biệt hoa/thường (Windows).
 */
export function normTarget(raw: unknown, projectDir?: string): string | null {
  const s = str(raw, 500);
  const m = /^(file|dwg):(.+)$/i.exec(s);
  if (!m) return null;
  const kind = m[1].toLowerCase();
  let p = m[2].trim().replace(/\\/g, "/");
  if (kind === "file") {
    if (projectDir && (isAbsolute(p) || /^[a-z]:\//i.test(p))) {
      const rel = relative(resolve(projectDir), resolve(p));
      if (rel && !rel.startsWith("..") && !isAbsolute(rel)) p = rel.replace(/\\/g, "/");
    }
    p = p.replace(/^(\.\/)+/, "").replace(/\/+$/, "");
    if (!p || p.split("/").includes("..")) return null;
  }
  return `${kind}:${p.replace(/\/{2,}/g, "/")}`;
}
const sameTarget = (a: string, b: string) => a.toLowerCase() === b.toLowerCase();

export class Board {
  readonly file: string; readonly logFile: string;
  private s: State = { version: 1, seq: 0, agents: {}, locks: [] };
  private queue: Promise<void> = Promise.resolve();
  private dirty = false; private logPending: string[] = [];
  /** Phiên đang có tiến trình agent chạy, kèm bộ hẹn giờ gia hạn khoá. */
  private running = new Map<string, NodeJS.Timeout>();
  private tokens = new Map<string, string>();   // token của lượt -> owner

  constructor(readonly dir: string) {
    const d = localDir(dir);
    this.file = join(d, "coord.json"); this.logFile = join(d, "coord-log.jsonl");
    rmSync(this.file + ".tmp", { force: true });   // file tạm sót lại sau lần sập giữa chừng
    try {
      const j = JSON.parse(readFileSync(this.file, "utf8"));
      if (j && typeof j === "object") this.s = { version: 1, seq: Number(j.seq) || 0, agents: j.agents && typeof j.agents === "object" ? j.agents : {}, locks: Array.isArray(j.locks) ? j.locks : [] };
    } catch { /* chưa có hoặc hỏng: bắt đầu bảng trống */ }
  }

  // ---------- ghi file ----------
  /** Xếp một lần ghi vào hàng đợi. Nhiều thay đổi liền nhau gộp thành một lần ghi coord.json. */
  private save() {
    this.dirty = true;
    this.queue = this.queue.then(async () => {
      if (this.logPending.length) {
        const lines = this.logPending.join(""); this.logPending = [];
        await appendFile(this.logFile, lines, "utf8");
        await this.trimLog();
      }
      if (!this.dirty) return;
      this.dirty = false;
      const tmp = this.file + ".tmp";
      await writeFile(tmp, JSON.stringify(this.s, null, 2), "utf8");
      await rename(tmp, this.file);
    }).catch(e => { console.error("coord: không ghi được bảng điều phối:", e?.message ?? e); });
  }
  private async trimLog() {
    let size = 0; try { size = statSync(this.logFile).size; } catch { return; }
    if (size <= LOG_MAX_BYTES) return;
    const keep = readFileSync(this.logFile, "utf8").split("\n").filter(Boolean).slice(-LOG_KEEP).join("\n") + "\n";
    const tmp = this.logFile + ".tmp";
    await writeFile(tmp, keep, "utf8"); await rename(tmp, this.logFile);
  }
  /** Chờ mọi lần ghi đang xếp hàng xong (test, tắt gateway). */
  flush() { return this.queue; }

  private log(m: Omit<Msg, "t">) {
    const full: Msg = { t: iso(), ...m };
    this.logPending.push(JSON.stringify(full) + "\n");
    this.save();
    return full;
  }
  /** Tin gần nhất (đọc file + phần chưa kịp ghi). */
  messages(limit = 100): Msg[] {
    let lines: string[] = [];
    try { lines = readFileSync(this.logFile, "utf8").split("\n"); } catch { /* chưa có */ }
    const out: Msg[] = [];
    for (const l of [...lines, ...this.logPending.map(x => x.trim())]) { if (!l.trim()) continue; try { out.push(JSON.parse(l)); } catch { /* dòng hỏng */ } }
    return out.slice(-limit);
  }

  // ---------- trạng thái ----------
  /** Bỏ khoá hết hạn (ghi tin hệ thống) và phiên rảnh quá lâu. Gọi trước mọi lần đọc/ghi. */
  private prune() {
    const now = clock();
    const dead = this.s.locks.filter(l => Date.parse(l.expires) <= now && !this.running.has(l.owner));
    if (dead.length) {
      this.s.locks = this.s.locks.filter(l => !dead.includes(l));
      this.log({ from: SYSTEM, to: "*", kind: "system", text: `Khoá hết hạn: ${dead.map(l => `${l.target} (${this.label(l.owner)})`).join(", ")}` });
    }
    for (const [id, a] of Object.entries(this.s.agents))
      if (a.status === "idle" && now - Date.parse(a.heartbeat) > AGENT_KEEP_MS && !this.s.locks.some(l => l.owner === id)) { delete this.s.agents[id]; this.dirty = true; }
  }
  label(owner: string) { return owner === USER ? "Người dùng" : owner === SYSTEM ? "Hệ thống" : this.s.agents[owner]?.label ?? owner; }
  snapshot() {
    this.prune();
    return { agents: this.s.agents, locks: this.s.locks, running: [...this.running.keys()], log: this.messages(100), now: iso() };
  }
  locksOf(owner: string) { this.prune(); return this.s.locks.filter(l => l.owner === owner); }

  // ---------- vòng đời lượt chat ----------
  /** Bắt đầu một lượt: phiên thành "working", gia hạn khoá định kỳ tới khi end(). Trả token cho MCP coord của lượt. */
  begin(owner: string, meta: { label: string; engine: string }): string {
    this.prune();
    const a = this.s.agents[owner];
    this.s.agents[owner] = { label: str(meta.label, 60) || owner, engine: meta.engine, task: a?.task ?? "", status: "working", heartbeat: iso() };
    clearInterval(this.running.get(owner));
    this.running.set(owner, setInterval(() => this.renew(owner), RENEW_MS).unref());
    this.renew(owner);
    const token = randomBytes(24).toString("base64url");
    this.tokens.set(token, owner);
    return token;
  }
  /** Gia hạn mọi khoá của phiên (tiến trình còn sống) và cập nhật heartbeat. */
  renew(owner: string) {
    const now = clock();
    for (const l of this.s.locks) if (l.owner === owner) {
      if (Date.parse(l.expires) < now + DEFAULT_TTL_MIN * 60_000) l.expires = iso(now + DEFAULT_TTL_MIN * 60_000);
    }
    const a = this.s.agents[owner]; if (a) a.heartbeat = iso(now);
    this.save();
  }
  /** Tiến trình agent đóng (xong, lỗi, bị dừng): thả mọi khoá của phiên, ghi tin hệ thống. */
  end(owner: string, token?: string, why = "phiên kết thúc lượt") {
    clearInterval(this.running.get(owner)); this.running.delete(owner);
    if (token) this.tokens.delete(token);
    const mine = this.s.locks.filter(l => l.owner === owner);
    this.s.locks = this.s.locks.filter(l => l.owner !== owner);
    const a = this.s.agents[owner];
    if (a) { a.status = "idle"; a.heartbeat = iso(); }
    if (mine.length) this.log({ from: SYSTEM, to: "*", kind: "system", text: `${this.label(owner)}: ${why}, đã thả khoá ${mine.map(l => l.target).join(", ")}` });
    this.save();
  }
  ownerOf(token: string | undefined) { return token ? this.tokens.get(token) : undefined; }
  /** Gateway vừa khởi động: không phiên nào còn chạy, mọi khoá còn lại là mồ côi. */
  cleanupOrphans() {
    const orphan = this.s.locks.filter(l => !this.running.has(l.owner));
    let changed = false;
    for (const a of Object.values(this.s.agents)) if (a.status === "working") { a.status = "idle"; changed = true; }
    if (orphan.length) {
      this.s.locks = this.s.locks.filter(l => !orphan.includes(l));
      this.log({ from: SYSTEM, to: "*", kind: "system", text: `Gateway khởi động lại: đã dọn ${orphan.length} khoá mồ côi (${orphan.map(l => `${l.target} của ${this.label(l.owner)}`).join(", ")})` });
    }
    if (changed || orphan.length) this.save();
    return orphan.length;
  }

  // ---------- thao tác của agent ----------
  claim(owner: string, input: { target?: unknown; mode?: unknown; reason?: unknown; ttl_min?: unknown }):
    { ok: true; lock: Lock } | { ok: false; busy: Lock; holder: string } | { error: string } {
    this.prune();
    const target = normTarget(input.target, this.dir);
    if (!target) return { error: "target phải có dạng file:<đường dẫn tương đối trong dự án> hoặc dwg:<đường dẫn đầy đủ bản vẽ>." };
    const mode = input.mode === "read" ? "read" : "write";
    const ttl = Math.min(MAX_TTL_MIN, Math.max(1, Number(input.ttl_min) || DEFAULT_TTL_MIN));
    const reason = str(input.reason, 120);
    const clash = this.s.locks.find(l => sameTarget(l.target, target) && l.owner !== owner && (l.mode === "write" || mode === "write"));
    if (clash) return { ok: false, busy: clash, holder: this.label(clash.owner) };
    const now = clock();
    let lock = this.s.locks.find(l => sameTarget(l.target, target) && l.owner === owner);
    if (lock) { lock.mode = mode === "write" ? "write" : lock.mode; lock.reason = reason || lock.reason; lock.expires = iso(now + ttl * 60_000); }
    else {
      lock = { id: `L${++this.s.seq}`, kind: target.startsWith("dwg:") ? "drawing" : "file", target, mode, owner, reason, since: iso(now), expires: iso(now + ttl * 60_000) };
      this.s.locks.push(lock);
      this.log({ from: owner, to: "*", kind: "lock", text: `giữ khoá ${mode === "write" ? "ghi" : "đọc"} ${target}${reason ? ` (${reason})` : ""}`, refs: [target] });
    }
    this.save();
    return { ok: true, lock };
  }
  /** Không cấp khoá, chỉ hỏi: phiên `owner` ghi vào target được không (giai đoạn 2: launcher hỏi trước tool ghi). */
  claimable(owner: string, raw: unknown): { ok: true } | { ok: false; holder: string; lock: Lock } | { error: string } {
    this.prune();
    const target = normTarget(raw, this.dir);
    if (!target) return { error: "target không hợp lệ." };
    const l = this.s.locks.find(x => sameTarget(x.target, target) && x.owner !== owner);
    return l ? { ok: false, holder: this.label(l.owner), lock: l } : { ok: true };
  }
  release(owner: string, input: { lock_id?: unknown; target?: unknown; note?: unknown }, force = false): { released: Lock[] } | { error: string } {
    this.prune();
    const id = str(input.lock_id, 20), target = input.target ? normTarget(input.target, this.dir) : null;
    if (!id && !target) return { error: "Cần lock_id hoặc target." };
    const hit = this.s.locks.filter(l => (id ? l.id === id : sameTarget(l.target, target!)) && (force || l.owner === owner));
    if (!hit.length) return { error: force ? "Không còn khoá này." : "Bạn không giữ khoá này (có thể đã hết hạn hoặc bị người dùng thu hồi)." };
    this.s.locks = this.s.locks.filter(l => !hit.includes(l));
    const note = str(input.note, 1000);
    if (force) this.log({ from: USER, to: "*", kind: "system", text: `Người dùng thu hồi khoá ${hit.map(l => `${l.target} của ${this.label(l.owner)}`).join(", ")}`, refs: hit.map(l => l.target) });
    else if (note) this.log({ from: owner, to: "*", kind: "handoff", text: note, refs: hit.map(l => l.target) });
    else this.log({ from: owner, to: "*", kind: "lock", text: `thả khoá ${hit.map(l => l.target).join(", ")}`, refs: hit.map(l => l.target) });
    this.save();
    return { released: hit };
  }
  post(from: string, input: { to?: unknown; kind?: unknown; text?: unknown; refs?: unknown }): { msg: Msg } | { error: string } {
    const text = str(input.text, 1000);
    if (!text) return { error: "Tin nhắn trống." };
    const to = str(input.to, 64) || "*";
    const kind = input.kind === "handoff" || input.kind === "question" ? input.kind : "note";
    const refs = Array.isArray(input.refs) ? input.refs.map(r => normTarget(r, this.dir) ?? str(r, 200)).filter(Boolean).slice(0, 10) : undefined;
    return { msg: this.log({ from, to, kind, text, ...(refs?.length ? { refs } : {}) }) };
  }
  task(owner: string, input: { task?: unknown; status?: unknown }): { agent: Agent } | { error: string } {
    const a = this.s.agents[owner];
    if (!a) return { error: "Phiên chưa đăng ký với bảng điều phối." };
    a.task = str(input.task, 120);
    if (input.status === "idle" || input.status === "working") a.status = input.status;
    a.heartbeat = iso();
    this.save();
    return { agent: a };
  }

  // ---------- văn bản cho agent ----------
  private lockLine(l: Lock) { return `${this.label(l.owner)} giữ khoá ${l.mode === "write" ? "ghi" : "đọc"} ${l.target} tới ${hhmm(l.expires)}${l.reason ? ` – ${l.reason}` : ""} [${l.id}]`; }
  private inbox(owner: string, n: number) { return this.messages(200).filter(m => m.from !== owner && (m.to === "*" || m.to === owner) && m.kind !== "lock").slice(-n); }
  /** Kết quả tool coord_status. */
  statusText(owner: string) {
    this.prune();
    const others = Object.entries(this.s.agents).filter(([id]) => id !== owner);
    const lines = [`Bạn là "${this.label(owner)}" (id ${owner}).`, "Phiên khác:"];
    lines.push(...(others.length ? others.map(([id, a]) => `- ${a.label} (${a.engine}, ${this.running.has(id) ? "đang chạy" : "rảnh"}, id ${id}): ${a.task || "chưa ghi việc"}`) : ["- (không có)"]));
    lines.push("Khoá đang giữ:", ...(this.s.locks.length ? this.s.locks.map(l => `- ${l.owner === owner ? "BẠN" : ""}${l.owner === owner ? " " : ""}${this.lockLine(l)}`) : ["- (không có)"]));
    const inbox = this.inbox(owner, 10);
    lines.push("Tin gần nhất gửi bạn hoặc mọi người:", ...(inbox.length ? inbox.map(m => `- ${hhmm(m.t)} ${this.label(m.from)} [${m.kind}]: ${m.text}`) : ["- (không có)"]));
    return lines.join("\n");
  }
  /** Khối chèn vào system prompt đầu mỗi lượt, tối đa 15 dòng. */
  promptBlock(owner: string): string {
    this.prune();
    const head = `Phối hợp (bảng điều phối của dự án; bạn là "${this.label(owner)}"):`;
    const rule = "Trước khi sửa file dự án hoặc vẽ/sửa bản vẽ AutoCAD, gọi coord_claim (target file:<đường dẫn tương đối> hoặc dwg:<đường dẫn bản vẽ>). Bị busy thì làm việc khác hoặc báo người dùng, không chờ lặp lại. Xong việc gọi coord_release kèm note bàn giao; đầu việc gọi coord_task.";
    const body: string[] = [];
    for (const [id, a] of Object.entries(this.s.agents)) if (id !== owner && this.running.has(id) && body.length < 4) body.push(`- ${a.label} (${a.engine}) đang làm: ${a.task || "chưa ghi việc"}`);
    const locks = this.s.locks.filter(l => l.owner !== owner);
    for (const l of locks.slice(0, 5)) body.push(`- ${this.lockLine(l)}`);
    if (locks.length > 5) body.push(`- … và ${locks.length - 5} khoá khác (xem coord_status)`);
    for (const m of this.inbox(owner, 3)) body.push(`- Tin ${hhmm(m.t)} từ ${this.label(m.from)} [${m.kind}]: ${m.text.slice(0, 160)}`);
    if (!body.length) body.push("- Hiện không có phiên nào khác đang giữ khoá.");
    return [head, ...body.slice(0, 13), rule].join("\n");
  }
}

// ---------- sổ bảng theo dự án ----------
const boards = new Map<string, Board>();
const key = (dir: string) => resolve(dir).toLowerCase();
/** Bảng của một thư mục dự án (tạo khi cần). Lần đầu mở trong tiến trình này thì dọn khoá mồ côi. */
export function boardFor(dir: string): Board {
  let b = boards.get(key(dir));
  if (!b) { b = new Board(dir); boards.set(key(dir), b); b.cleanupOrphans(); }
  return b;
}
/** Chỉ cho test: giả lập gateway khởi động lại (quên mọi bảng trong bộ nhớ). */
export function _resetBoards() { for (const b of boards.values()) for (const o of b.snapshot().running) b.end(o, undefined, "test"); boards.clear(); }
/** Chờ mọi bảng ghi xong (tắt gateway, test). */
export const flushAll = () => Promise.all([...boards.values()].map(b => b.flush()));
export function boardByToken(token: string | undefined): { board: Board; owner: string } | undefined {
  if (!token) return;
  for (const b of boards.values()) { const owner = b.ownerOf(token); if (owner) return { board: b, owner }; }
}

// ---------- tool MCP ----------
export const COORD_TOOLS = [
  { name: "coord_status", description: "Xem bảng điều phối của dự án: phiên nào đang làm gì, khoá nào đang giữ, 10 tin gần nhất gửi bạn hoặc mọi người.", inputSchema: { type: "object", properties: {} } },
  { name: "coord_claim", description: "Xin khoá trước khi sửa một file dự án hoặc vẽ/sửa một bản vẽ AutoCAD. Kết quả 'ok' kèm lock_id, hoặc 'busy' kèm phiên đang giữ. Khoá tự gia hạn khi bạn còn chạy và tự thả khi lượt kết thúc.", inputSchema: { type: "object", properties: {
    target: { type: "string", description: "file:<đường dẫn tương đối trong dự án> hoặc dwg:<đường dẫn đầy đủ của bản vẽ>" },
    mode: { type: "string", enum: ["write", "read"], description: "write (mặc định) chặn mọi phiên khác; read chỉ chặn phiên muốn ghi" },
    reason: { type: "string", description: "Làm gì với nó, rất ngắn (vd: vẽ lưới trục)" },
    ttl_min: { type: "number", description: "Hạn khoá tính bằng phút, mặc định 10" } }, required: ["target", "reason"] } },
  { name: "coord_release", description: "Thả khoá khi xong việc. Có note thì note thành tin bàn giao cho các phiên khác.", inputSchema: { type: "object", properties: {
    lock_id: { type: "string" }, target: { type: "string" }, note: { type: "string", description: "Ghi chú bàn giao: đã làm gì, phiên sau cần biết gì" } } } },
  { name: "coord_post", description: "Gửi tin cho phiên khác hoặc mọi người (to='*').", inputSchema: { type: "object", properties: {
    to: { type: "string", description: "'*' hoặc id phiên" }, kind: { type: "string", enum: ["note", "handoff", "question"] }, text: { type: "string" },
    refs: { type: "array", items: { type: "string" } } }, required: ["text"] } },
  { name: "coord_task", description: "Ghi việc bạn đang làm (hiện ở dải 'Đang làm' cho người dùng và các phiên khác).", inputSchema: { type: "object", properties: {
    task: { type: "string" }, status: { type: "string", enum: ["working", "idle"] } }, required: ["task"] } },
] as const;
export const COORD_TOOL_NAMES = COORD_TOOLS.map(t => t.name);

/** Chạy một tool coord cho phiên `owner`. Trả văn bản cho agent; busy KHÔNG phải lỗi (dòng đầu bắt đầu bằng "busy:"). */
export function runTool(board: Board, owner: string, name: string, args: any): { text: string; isError?: boolean } {
  args = args && typeof args === "object" ? args : {};
  const err = (e: string) => ({ text: e, isError: true });
  switch (name) {
    case "coord_status": return { text: board.statusText(owner) };
    case "coord_claim": {
      const r = board.claim(owner, args);
      if ("error" in r) return err(r.error);
      if (r.ok) return { text: `ok: ${r.lock.id} ${r.lock.mode === "write" ? "ghi" : "đọc"} ${r.lock.target} tới ${hhmm(r.lock.expires)} (tự gia hạn khi bạn còn chạy).` };
      return { text: `busy: Chờ ${r.holder} – ${r.busy.reason || "đang sửa"} (tới ${hhmm(r.busy.expires)})\n${r.busy.target} đang bị khoá ${r.busy.mode === "write" ? "ghi" : "đọc"} [${r.busy.id}]. Đừng sửa nó; làm phần việc khác, hoặc coord_post hỏi ${r.holder} (to=${r.busy.owner}), hoặc báo người dùng.` };
    }
    case "coord_release": { const r = board.release(owner, args); return "error" in r ? err(r.error) : { text: `Đã thả ${r.released.map(l => `${l.id} ${l.target}`).join(", ")}.` }; }
    case "coord_post": { const r = board.post(owner, args); return "error" in r ? err(r.error) : { text: `Đã gửi tới ${r.msg.to}.` }; }
    case "coord_task": { const r = board.task(owner, args); return "error" in r ? err(r.error) : { text: `Đã ghi việc: ${r.agent.task || "(trống)"}.` }; }
  }
  return err("Tool không tồn tại.");
}

