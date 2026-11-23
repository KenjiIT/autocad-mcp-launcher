// Kiểm thử Playwright: phiên A đang chạy (CLI giả chạy chậm 7 giây) thì vẫn tạo được phiên B, gửi tin ở B, quay lại A thấy A xong.
// Hội thoại và /api/chat được giả lập trong trình duyệt (page.route) nên không ghi gì vào dự án thật.
// Chạy khi CAD Studio đang mở ở http://localhost:5176:
//   npm i --no-save playwright-core && node scripts/e2e/multi-session.mjs <thư mục lưu ảnh>
// Dùng Edge có sẵn trên máy (đổi EDGE nếu cần). Thoát mã khác 0 khi hỏng.
import { chromium } from "playwright-core";
const OUT = process.argv[2] ?? ".";
const EDGE = process.env.EDGE ?? "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
const b = await chromium.launch({ executablePath: EDGE });
const pg = await b.newPage({ viewport: { width: 1440, height: 900 } });
const convs = new Map();   // hội thoại giả trong bộ nhớ: không ghi vào dự án thật
const meta = c => ({ id: c.id, title: c.title, updatedAt: c.updatedAt, engine: c.engine ?? "cli" });
await pg.route(/\/api\/conversations(\/[^?]+)?(\?.*)?$/, async r => {
  const m = /\/api\/conversations\/([^?]+)/.exec(r.request().url()); const method = r.request().method();
  if (!m) return r.fulfill({ json: { conversations: [...convs.values()].sort((a, b) => b.updatedAt - a.updatedAt).map(meta) } });
  const id = decodeURIComponent(m[1]);
  if (method === "PUT") { const body = JSON.parse(r.request().postData() || "{}"); const c = { ...(convs.get(id) ?? { id, title: "Phiên chat mới", items: [], history: [] }), ...body, id, updatedAt: Date.now() }; convs.set(id, c); return r.fulfill({ json: meta(c) }); }
  if (method === "DELETE") { convs.delete(id); return r.fulfill({ json: { ok: true } }); }
  return convs.has(id) ? r.fulfill({ json: convs.get(id) }) : r.fulfill({ status: 404, json: { error: "x" } });
});
const sse = (txt, sid) => `event: text\ndata: ${JSON.stringify(txt)}\n\nevent: done\ndata: ${JSON.stringify({ messages: [], sessionId: sid })}\n\n`;
const log = []; 
await pg.route("**/api/chat", async r => {
  const body = JSON.parse(r.request().postData());
  const last = body.messages[body.messages.length - 1].content;
  log.push(`chat ${last} @${Date.now()}`);
  if (String(last).includes("câu A")) { await new Promise(res => setTimeout(res, 7000)); return r.fulfill({ status: 200, headers: { "Content-Type": "text/event-stream" }, body: sse("Xong A (CLI giả chạy chậm 7 giây)", "sa") }); }
  return r.fulfill({ status: 200, headers: { "Content-Type": "text/event-stream" }, body: sse("Xong B ngay", "sb") });
});
await pg.goto("http://localhost:5176/"); await pg.waitForSelector(".prow"); await pg.waitForTimeout(1500);
const ta = pg.locator("textarea").first();
await ta.fill("câu A"); await ta.press("Enter");
await pg.waitForSelector(".prun"); await pg.waitForTimeout(400);
await pg.screenshot({ path: `${OUT}/6a-A-dang-chay.png` });
const addBtn = pg.locator(".pnode.cur .prow-add");
log.push("+ disabled=" + await addBtn.isDisabled());
await addBtn.click(); await pg.waitForTimeout(500);
await pg.getByRole("menuitem", { name: /^✳?\s*Claude/ }).first().click().catch(() => pg.locator(".ctxmenu button, [role=menuitem]").filter({ hasText: "Claude" }).first().click());
await pg.waitForTimeout(800);
log.push("sau tạo phiên: " + JSON.stringify(await pg.locator(".msgs .user, .chat .user").allTextContents()) + " items=" + await pg.locator(".pconvs li").count());
await pg.screenshot({ path: `${OUT}/dbg-new.png` });
await ta.fill("câu B"); await ta.press("Enter");
await pg.getByText("Xong B ngay").waitFor({ timeout: 5000 });
log.push("A vẫn chạy khi B xong: " + (await pg.locator(".prun").count()));
await pg.screenshot({ path: `${OUT}/6b-B-xong-A-van-chay.png` });
await pg.locator(".pconvs .pick", { hasText: "câu A" }).first().click();
await pg.getByText("Xong A (CLI giả chạy chậm 7 giây)").waitFor({ timeout: 15000 }).catch(async e => { await pg.screenshot({ path: `${OUT}/dbg-A.png` }); console.log(log.join(" | ")); console.log(JSON.stringify([...convs.values()].map(c => [c.id, c.title, (c.items || []).length]))); throw e; });
await pg.waitForTimeout(400);
log.push("A xong, chấm chạy còn: " + (await pg.locator(".prun").count()));
log.push("đã lưu: " + [...convs.values()].map(c => `${c.title}=${(c.items || []).length} mục`).join(", "));
await pg.screenshot({ path: `${OUT}/6c-quay-lai-A-da-xong.png` });
await b.close();
console.log(log.join("\n"));
if (!log.some(l => l.startsWith("A xong, chấm chạy còn: 0")) || log.includes("+ disabled=true")) { console.error("HỎNG"); process.exit(1); }
