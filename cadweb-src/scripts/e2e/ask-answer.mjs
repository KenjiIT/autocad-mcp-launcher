// Playwright: trả lời câu hỏi của agent khi lượt đang chạy, thẻ phải chuyển sang "đã trả lời" và không bị stream ghi đè (lỗi sau khi chạy nhiều phiên). Chạy: node scripts/e2e/ask-answer.mjs <thư mục ảnh>
import { chromium } from "playwright-core";
const OUT = process.argv[2];
const b = await chromium.launch({ executablePath: "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" });
const pg = await b.newPage({ viewport: { width: 1280, height: 900 }, colorScheme: "dark" });
const convs = new Map();
await pg.route(/\/api\/conversations(\/[^?]+)?(\?.*)?$/, async r => {
  const m = /\/api\/conversations\/([^?]+)/.exec(r.request().url()); const method = r.request().method();
  if (!m) return r.fulfill({ json: { conversations: [...convs.values()] } });
  const id = decodeURIComponent(m[1]);
  if (method === "PUT") { const c = { ...(convs.get(id) ?? { id, title: "x", items: [], history: [], engine: "cli" }), ...JSON.parse(r.request().postData() || "{}"), id, updatedAt: Date.now() }; convs.set(id, c); return r.fulfill({ json: c }); }
  return convs.has(id) ? r.fulfill({ json: convs.get(id) }) : r.fulfill({ status: 404, json: {} });
});
await pg.addInitScript(() => {
  const real = window.fetch.bind(window);
  window.fetch = async (url, opt) => {
    const u = String(url);
    if (u.includes("/api/ask")) { window.__answered = true; return new Response(JSON.stringify({ ok: true }), { headers: { "Content-Type": "application/json" } }); }
    if (!u.includes("/api/chat")) return real(url, opt);
    const enc = new TextEncoder(); const ev = (e, d) => enc.encode(`event: ${e}\ndata: ${JSON.stringify(d)}\n\n`);
    const q = (id, header, question, labels) => ({ id, questions: [{ header, question, multiSelect: false, options: labels.map(l => ({ label: l, description: "mô tả " + l })) }] });
    const body = new ReadableStream({ async start(c) {
      c.enqueue(ev("ask", q("a1", "Hướng đi", "Bạn muốn tôi làm gì tiếp?", ["Giữ nguyên", "Dựng nhà mới"])));
      while (!window.__answered) await new Promise(r => setTimeout(r, 100));
      await new Promise(r => setTimeout(r, 300));
      c.enqueue(ev("text", "Được, tôi hỏi tiếp về lô đất."));
      c.enqueue(ev("ask", q("a2", "Loại nhà", "Lô đất và loại nhà?", ["Nhà phố 5x20", "Nhà vườn"])));
      await new Promise(r => setTimeout(r, 1500));
      c.enqueue(ev("done", { messages: [], sessionId: "s" })); c.close();
    } });
    return new Response(body, { headers: { "Content-Type": "text/event-stream" } });
  };
});
await pg.goto("http://localhost:5176/"); await pg.waitForSelector("textarea"); await pg.waitForTimeout(1200);
const ta = pg.locator("textarea").first(); await ta.fill("vẽ 1 căn nhà"); await ta.press("Enter");
await pg.waitForSelector("form.ask-card"); await pg.locator("form.ask-card .ask-opt", { hasText: "Dựng nhà mới" }).click();
await pg.locator("form.ask-card button.primary").click();
await pg.waitForTimeout(1200);
const forms = await pg.locator("form.ask-card").count(), done = await pg.locator(".ask-card.ask-done").count();
console.log("thẻ còn dạng form:", forms, "| thẻ đã trả lời:", done);
await pg.screenshot({ path: `${OUT}/ask-sau-khi-tra-loi.png` });
await b.close();
console.log(forms === 1 && done === 1 ? "ĐÚNG: câu 1 hiện đã trả lời, chỉ câu 2 còn chờ" : "LỖI");
