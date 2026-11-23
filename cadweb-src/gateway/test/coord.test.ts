import { test, after } from "node:test";
import assert from "node:assert/strict";
import http from "node:http";
import { existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const DIR = mkdtempSync(join(tmpdir(), "cad-coord-"));
process.env.CAD_DATA_DIR = join(DIR, "app") + "/";
const C = await import("../src/coord.js");
after(async () => { await C.flushAll(); rmSync(DIR, { recursive: true, force: true }); });   // không để rác trong %TEMP%
const { codexArgs } = await import("../src/codex.js");
const { COORD_MCP } = await import("../src/cli.js");

let n = 0;
const mk = async () => { const d = join(DIR, `p${++n}`); mkdirSync(d, { recursive: true }); return d; };
const readState = (d: string) => JSON.parse(readFileSync(join(d, ".cadstudio", "coord.json"), "utf8"));
const readLog = (d: string) => readFileSync(join(d, ".cadstudio", "coord-log.jsonl"), "utf8").trim().split("\n").map(l => JSON.parse(l));

test("chuẩn hoá target", () => {
  assert.equal(C.normTarget("file:.\\bao-cao\\a.xlsx"), "file:bao-cao/a.xlsx");
  assert.equal(C.normTarget("dwg:D:\\DuAn\\KT-02.dwg"), "dwg:D:/DuAn/KT-02.dwg");
  assert.equal(C.normTarget("file:C:/P/x/y.txt", "C:/P"), "file:x/y.txt");
  for (const bad of ["", "KT.dwg", "file:../ngoai.txt", "http:x", 3]) assert.equal(C.normTarget(bad), null, String(bad));
});

test("hai phiên tranh khoá: busy, bàn giao, rồi được cấp", async () => {
  const d = await mk(); const b = C.boardFor(d);
  const ta = b.begin("conv-aaaa-0001", { label: "Chat 1", engine: "claude" });
  const tb = b.begin("conv-bbbb-0002", { label: "Chat 2", engine: "codex" });
  assert.equal(C.boardByToken(ta)?.owner, "conv-aaaa-0001");
  const r1 = C.runTool(b, "conv-aaaa-0001", "coord_claim", { target: "dwg:D:/DuAn/KT-02.dwg", reason: "vẽ lưới trục" });
  assert.match(r1.text, /^ok: L1 /);
  // khác hoa/thường, dấu \ vẫn là cùng bản vẽ
  const r2 = C.runTool(b, "conv-bbbb-0002", "coord_claim", { target: "dwg:d:\\duan\\kt-02.DWG", reason: "đặt cửa" });
  assert.ok(!r2.isError, "busy không phải lỗi");
  assert.match(r2.text, /^busy: Chờ Chat 1 – vẽ lưới trục \(tới \d\d:\d\d\)/);
  assert.match(C.runTool(b, "conv-bbbb-0002", "coord_claim", { target: "dwg:D:/DuAn/KT-02.dwg", mode: "read", reason: "đo" }).text, /^busy/, "đọc cũng bị chặn khi có khoá ghi");
  assert.match(C.runTool(b, "conv-bbbb-0002", "coord_claim", { target: "file:bao-cao/thong-ke-cua.xlsx", reason: "bảng cửa" }).text, /^ok: L2/);
  assert.match(b.promptBlock("conv-bbbb-0002"), /Chat 1 giữ khoá ghi dwg:D:\/DuAn\/KT-02\.dwg/);
  assert.ok(C.runTool(b, "conv-bbbb-0002", "coord_release", { lock_id: "L1" }).isError, "không thả khoá của người khác");
  assert.match(C.runTool(b, "conv-aaaa-0001", "coord_release", { lock_id: "L1", note: "Lưới trục xong, layer A-GRID" }).text, /Đã thả L1/);
  assert.match(b.statusText("conv-bbbb-0002"), /Chat 1 \[handoff\]: Lưới trục xong/);
  assert.match(C.runTool(b, "conv-bbbb-0002", "coord_claim", { target: "dwg:D:/DuAn/KT-02.dwg", reason: "đặt cửa" }).text, /^ok: L3/);
  assert.match(C.runTool(b, "conv-bbbb-0002", "coord_task", { task: "Đặt cửa tầng 2" }).text, /Đặt cửa tầng 2/);
  assert.match(C.runTool(b, "conv-aaaa-0001", "coord_post", { to: "*", kind: "question", text: "Cửa xong chưa?" }).text, /Đã gửi tới \*/);
  // hai khoá đọc cùng lúc được
  assert.match(C.runTool(b, "conv-aaaa-0001", "coord_claim", { target: "file:hs/a.pdf", mode: "read", reason: "đọc" }).text, /^ok/);
  assert.match(C.runTool(b, "conv-bbbb-0002", "coord_claim", { target: "file:hs/a.pdf", mode: "read", reason: "đọc" }).text, /^ok/);
  b.end("conv-aaaa-0001", ta); b.end("conv-bbbb-0002", tb);
  assert.equal(C.boardByToken(ta), undefined, "hết lượt thì token hết hiệu lực");
  await b.flush();
  const kinds = readLog(d).map(m => m.kind);
  assert.ok(kinds.includes("handoff") && kinds.includes("question") && kinds.includes("system"));
});

test("phiên chết giữa chừng: thả ngay mọi khoá, ghi tin hệ thống", async () => {
  const d = await mk(); const b = C.boardFor(d);
  const t = b.begin("conv-dead-0001", { label: "Chat chết", engine: "codex" });
  b.claim("conv-dead-0001", { target: "dwg:D:/A.dwg", reason: "x" });
  b.claim("conv-dead-0001", { target: "file:a.txt", reason: "y" });
  b.end("conv-dead-0001", t, "người dùng dừng lượt");
  assert.equal(b.snapshot().locks.length, 0);
  assert.equal(b.snapshot().agents["conv-dead-0001"].status, "idle");
  await b.flush();
  assert.match(readLog(d).at(-1).text, /Chat chết: người dùng dừng lượt, đã thả khoá dwg:D:\/A\.dwg, file:a\.txt/);
  assert.equal(readState(d).locks.length, 0);
});

test("khoá tự gia hạn khi tiến trình còn chạy, hết hạn khi không", async () => {
  const d = await mk(); const b = C.boardFor(d);
  let now = Date.parse("2026-11-21T09:00:00Z"); C._setClock(() => now);
  try {
    const t = b.begin("conv-live-0001", { label: "Sống", engine: "claude" });
    b.claim("conv-live-0001", { target: "file:a.txt", reason: "x", ttl_min: 2 });
    now += 5 * 60_000;
    assert.equal(b.snapshot().locks.length, 1, "đang chạy thì không hết hạn");
    b.renew("conv-live-0001");
    assert.ok(Date.parse(b.snapshot().locks[0].expires) > now);
    clearInterval((b as any).running.get("conv-live-0001")); (b as any).running.delete("conv-live-0001");   // giả lập mất tiến trình mà không qua end()
    now += 11 * 60_000;
    assert.equal(b.snapshot().locks.length, 0, "hết hạn thì bị bỏ");
    assert.match(b.messages().at(-1)!.text, /Khoá hết hạn: file:a\.txt/);
    void t;
  } finally { C._setClock(() => Date.now()); }
});

test("gateway khởi động lại: khoá mồ côi được dọn, phiên về rảnh", async () => {
  const d = await mk(); const b = C.boardFor(d);
  b.begin("conv-orph-0001", { label: "Mồ côi", engine: "claude" });
  b.claim("conv-orph-0001", { target: "dwg:D:/B.dwg", reason: "z" });
  await b.flush();
  assert.equal(readState(d).locks.length, 1);
  // Giả lập gateway sập: quên bảng trong bộ nhớ mà KHÔNG gọi end(), rồi mở lại như lúc khởi động.
  clearInterval((b as any).running.get("conv-orph-0001"));
  (b as any).running.delete("conv-orph-0001");
  C._resetBoards();   // chỉ quên bảng trong bộ nhớ (phiên đã bỏ khỏi running nên không gọi end): khoá vẫn còn trên đĩa
  assert.equal(readState(d).locks.length, 1);
  const b2 = C.boardFor(d);
  assert.notEqual(b2, b);
  assert.equal(b2.snapshot().locks.length, 0);
  assert.equal(b2.snapshot().agents["conv-orph-0001"].status, "idle");
  await b2.flush();
  assert.equal(readState(d).locks.length, 0);
  assert.match(readLog(d).at(-1).text, /dọn 1 khoá mồ côi/);
});

test("ghi atomic qua hàng đợi: nhiều thao tác dồn dập, file luôn là JSON hợp lệ, không sót file tạm", async () => {
  const d = await mk(); const b = C.boardFor(d);
  b.begin("conv-many-0001", { label: "Nhiều", engine: "claude" });
  for (let i = 0; i < 200; i++) { b.claim("conv-many-0001", { target: `file:f${i}.txt`, reason: "r" }); if (i % 3 === 0) b.release("conv-many-0001", { target: `file:f${i}.txt` }); }
  await b.flush();
  const st = readState(d);
  assert.equal(st.locks.length, 200 - 67);
  assert.deepEqual(readdirSync(join(d, ".cadstudio")).filter(f => f.endsWith(".tmp")), []);
  b.end("conv-many-0001");
});

test("người dùng gửi tin to:* và thu hồi khoá", async () => {
  const d = await mk(); const b = C.boardFor(d);
  b.begin("conv-user-0001", { label: "Kẹt", engine: "claude" });
  const r: any = b.claim("conv-user-0001", { target: "file:x.dwg", reason: "kẹt" });
  assert.ok("released" in b.release(C.USER, { lock_id: r.lock.id }, true));
  assert.equal(b.locksOf("conv-user-0001").length, 0);
  assert.ok("msg" in b.post(C.USER, { text: "Dừng vẽ KT-02, để tôi sửa tay" }));
  assert.match(b.promptBlock("conv-user-0001"), /Người dùng \[note\]: Dừng vẽ KT-02/);
  b.end("conv-user-0001");
});

test("khối system prompt không quá 15 dòng", async () => {
  const d = await mk(); const b = C.boardFor(d);
  for (let i = 0; i < 8; i++) { b.begin(`conv-load-000${i}`, { label: `Chat ${i}`, engine: "claude" }); b.claim(`conv-load-000${i}`, { target: `file:f${i}`, reason: "r" }); b.post(`conv-load-000${i}`, { text: `tin ${i}` }); }
  const lines = b.promptBlock("conv-me-00000001").split("\n");
  assert.ok(lines.length <= 15, String(lines.length));
  assert.match(lines.at(-1)!, /coord_claim/);
  for (let i = 0; i < 8; i++) b.end(`conv-load-000${i}`);
});

test("Codex nhận MCP coord qua -c và chỉ dẫn có khối tình trạng", () => {
  const { args } = codexArgs({ model: "x", servers: [], allowed: [], coord: { url: "http://127.0.0.1:1/internal/coord", token: "tok", prompt: "Phối hợp: XYZ" } });
  const c = args.flatMap((a, i) => (args[i - 1] === "-c" ? [a] : []));
  assert.ok(c.includes('mcp_servers.coord.env.COORD_TOKEN="tok"'));
  assert.ok(c.includes('mcp_servers.coord.default_tools_approval_mode="approve"'));
  assert.ok(c.some(x => x.startsWith("developer_instructions=") && x.includes("Phối hợp: XYZ")));
});

test("coord-mcp.mjs: 5 tool, chuyển lời gọi về gateway kèm token", async () => {
  const d = await mk(); const b = C.boardFor(d);
  const token = b.begin("conv-mcp0-0001", { label: "MCP", engine: "claude" });
  const srv = http.createServer((req, res) => {
    let body = ""; req.on("data", x => { body += x; }); req.on("end", () => {
      const hit = C.boardByToken(String(req.headers["x-coord-token"]));
      const j = JSON.parse(body);
      res.writeHead(hit ? 200 : 401, { "content-type": "application/json" });
      res.end(JSON.stringify(hit ? C.runTool(hit.board, hit.owner, j.tool, j.args) : { error: "token" }));
    });
  });
  await new Promise<void>(r => srv.listen(0, "127.0.0.1", r));
  const port = (srv.address() as any).port;
  const client = new Client({ name: "t", version: "1" });
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [COORD_MCP], env: { ...process.env as any, COORD_URL: `http://127.0.0.1:${port}/internal/coord`, COORD_TOKEN: token, COORD_TOOLS: JSON.stringify(C.COORD_TOOLS) } }));
  try {
    assert.deepEqual((await client.listTools()).tools.map(t => t.name).sort(), [...C.COORD_TOOL_NAMES].sort());
    const r: any = await client.callTool({ name: "coord_claim", arguments: { target: "file:a.txt", reason: "thử" } });
    assert.match(r.content[0].text, /^ok:/);
    assert.equal(b.locksOf("conv-mcp0-0001").length, 1);
  } finally { await client.close(); srv.close(); b.end("conv-mcp0-0001", token); }
  assert.ok(existsSync(COORD_MCP));
});
