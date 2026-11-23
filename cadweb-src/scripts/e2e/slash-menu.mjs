// Kiểm thử Playwright: gõ "/" ở giữa câu mở menu skill, lọc theo chữ, Enter chèn đúng chỗ con trỏ; "/" trong C:/ không mở;
// gửi tin có skill ở giữa câu thì lời nhắn gửi agent có dặn nạp skill. /api/chat và hội thoại giả lập trong trình duyệt.
// Chạy khi CAD Studio mở ở http://localhost:5176:  npm i --no-save playwright-core && node scripts/e2e/slash-menu.mjs <thư mục ảnh>
import { chromium } from "playwright-core";
const OUT = process.argv[2] ?? ".";
const EDGE = process.env.EDGE ?? "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
const b = await chromium.launch({ executablePath: EDGE });
const pg = await b.newPage({ viewport: { width: 1440, height: 900 } });
const convs = new Map();
await pg.route(/\/api\/conversations(\/[^?]+)?(\?.*)?$/, async r => {
  const m = /\/api\/conversations\/([^?]+)/.exec(r.request().url()); const method = r.request().method();
  if (!m) return r.fulfill({ json: { conversations: [...convs.values()].map(c => ({ id: c.id, title: c.title, updatedAt: c.updatedAt, engine: "cli" })) } });
  const id = decodeURIComponent(m[1]);
  if (method === "PUT") { const c = { ...(convs.get(id) ?? { id, title: "Phiên chat mới", items: [], history: [] }), ...JSON.parse(r.request().postData() || "{}"), id, updatedAt: Date.now() }; convs.set(id, c); return r.fulfill({ json: c }); }
  return convs.has(id) ? r.fulfill({ json: convs.get(id) }) : r.fulfill({ status: 404, json: {} });
});
let sent = "";
await pg.route("**/api/chat", async r => {
  const body = JSON.parse(r.request().postData()); sent = String(body.messages[body.messages.length - 1].content);
  r.fulfill({ status: 200, headers: { "Content-Type": "text/event-stream" }, body: `event: text\ndata: "ok"\n\nevent: done\ndata: {"messages":[],"sessionId":"s"}\n\n` });
});
const fail = m => { console.error("HỎNG:", m); process.exitCode = 1; };
await pg.goto("http://localhost:5176/"); await pg.waitForSelector("textarea"); await pg.waitForTimeout(1500);
const skills = await pg.evaluate(() => fetch("/api/skills").then(r => r.json()).then(j => j.skills.map(s => s.name)));
const ta = pg.locator("textarea").first(); const menu = pg.locator(".slash");
await ta.click(); await ta.pressSequentially("mở C:/");
if (await menu.count() && await menu.isVisible()) fail("'/' trong C:/ không được mở menu");
await ta.fill(""); await ta.pressSequentially("phương án nhà này xấu quá bạn không dùng /");
await pg.waitForTimeout(300);
if (!(await menu.isVisible())) fail("'/' giữa câu phải mở menu");
await pg.screenshot({ path: `${OUT}/7a-slash-giua-cau.png` });
const q = skills[0].slice(0, 5);
await ta.pressSequentially(q); await pg.waitForTimeout(300);
const first = await menu.locator("li").first().innerText();
await pg.screenshot({ path: `${OUT}/7b-slash-loc.png` });
await ta.press("Enter"); await pg.waitForTimeout(200);
const v = await ta.inputValue();
const name = first.split("\n")[0].trim();
console.log("menu đầu tiên:", name, "| ô soạn:", JSON.stringify(v));
if (!v.startsWith("phương án nhà này xấu quá bạn không dùng /")) fail("phần chữ trước bị mất");
if (!/ \/[\w-]+ $/.test(v)) fail("chưa chèn /tên-skill tại con trỏ");
await ta.pressSequentially("cho nhà 2 tầng"); await ta.press("Escape");
await pg.screenshot({ path: `${OUT}/7c-da-chen.png` });
await ta.press("Enter"); await pg.waitForTimeout(800);
console.log("gửi agent:", sent.slice(0, 160).replace(/\n/g, " ⏎ "));
if (!/^Hãy dùng skill "/.test(sent)) fail("skill giữa câu phải được dặn nạp");
await pg.screenshot({ path: `${OUT}/7d-bong-bong-chip.png` });
await b.close();
