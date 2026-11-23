// Playwright: Esc dừng lượt đang chạy, tin vừa gửi về lại ô soạn; nút Sửa trên tin cuối đưa tin về ô soạn. Chạy: node scripts/e2e/esc-edit.mjs <thư mục ảnh>
import { chromium } from "playwright-core";
const OUT = process.argv[2];
const b = await chromium.launch({ executablePath: "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" });
const pg = await b.newPage({ viewport: { width: 1280, height: 820 }, colorScheme: "dark" });
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
    if (!String(url).includes("/api/chat")) return real(url, opt);
    const sig = opt?.signal;
    const enc = new TextEncoder();
    const body = new ReadableStream({ start(c) {
      c.enqueue(enc.encode(`event: text\ndata: ${JSON.stringify("Đang tìm chỗ đặt bàn gaming…")}\n\n`));
      sig?.addEventListener("abort", () => c.error(new DOMException("Aborted", "AbortError")));
    } });
    if (sig?.aborted) throw new DOMException("Aborted", "AbortError");
    return new Response(body, { headers: { "Content-Type": "text/event-stream" } });
  };
});
const log = [];
await pg.goto("http://localhost:5176/"); await pg.waitForSelector("textarea"); await pg.waitForTimeout(1200);
const ta = pg.locator("textarea").first();
const msg = "tôi có bàn gaming kèm màn hình, kèm ghế tìm chỗ nhét vào cho tôi";
await ta.fill(msg); await ta.press("Enter"); await pg.waitForTimeout(800);
log.push("đang chạy: " + (await pg.locator("button.send.stop").count()));
await pg.locator(".msgs").click({ position: { x: 20, y: 20 } }).catch(() => {});
await pg.keyboard.press("Escape"); await pg.waitForTimeout(800);
log.push("sau Esc còn chạy: " + (await pg.locator("button.send.stop").count()));
log.push("ô soạn: " + JSON.stringify(await ta.inputValue()));
await pg.screenshot({ path: `${OUT}/esc-sau-khi-dung.png` });
await ta.fill("");
await pg.locator(".bubble.user").last().hover(); await pg.waitForTimeout(300);
await pg.screenshot({ path: `${OUT}/sua-tin-hover.png` });
await pg.locator(".edit-msg").click({ trial: true }); log.push("nút Sửa bấm được (không cần force): ok"); await pg.locator(".edit-msg").click(); await pg.waitForTimeout(400);
log.push("sau Sửa: ô soạn = " + JSON.stringify(await ta.inputValue()) + ", số tin của mình = " + (await pg.locator(".bubble.user").count()));
await b.close();
console.log(log.join("\n"));
