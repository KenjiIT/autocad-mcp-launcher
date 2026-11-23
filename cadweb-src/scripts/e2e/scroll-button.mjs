// Playwright: nút "xuống cuối" ở góc phải dưới khung chat (sáng, tối, cửa sổ hẹp); hội thoại dài được giả lập. Chạy: node scripts/e2e/scroll-button.mjs <thư mục ảnh> sau
import { chromium } from "playwright-core";
const [OUT, tag] = [process.argv[2], process.argv[3]];
const b = await chromium.launch({ executablePath: "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" });
const svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 300"><rect width="500" height="300" fill="#dfe9f0"/><rect x="20" y="20" width="460" height="260" fill="none" stroke="#16212b" stroke-width="6"/><text x="250" y="160" font-size="28" text-anchor="middle">Mặt bằng PA-A</text></svg>';
const items = [];
for (let i = 0; i < 8; i++) { items.push({ kind: "user", text: `Câu hỏi ${i + 1}` }); items.push({ kind: "text", text: `Trả lời ${i + 1}\n\n\`\`\`svg\n${svg}\n\`\`\`\n\nPhương án ${i + 1} với các phòng chính.` }); }
const conv = { id: "c1", title: "Phiên dài", updatedAt: Date.now(), engine: "cli", items, history: [] };
for (const [scheme, w] of [["light", 1280], ["dark", 1280], ["light-hep", 760]]) {
  const pg = await b.newPage({ viewport: { width: 1280, height: 820 }, colorScheme: scheme.startsWith("dark") ? "dark" : "light" });
  await pg.route(/\/api\/conversations(\/[^?]+)?(\?.*)?$/, r => /conversations\/c1/.test(r.request().url()) ? r.fulfill({ json: conv }) : r.request().method() === "GET" ? r.fulfill({ json: { conversations: [conv] } }) : r.fulfill({ json: conv }));
  await pg.goto("http://localhost:5176/"); await pg.waitForSelector(".pconvs .pick"); await pg.waitForTimeout(800);
  await pg.locator(".pconvs .pick", { hasText: "Phiên dài" }).first().click(); await pg.waitForTimeout(1500);
  if (w !== 1280) { await pg.setViewportSize({ width: w, height: 820 }); await pg.waitForTimeout(600); }
  await pg.locator(".msgs").evaluate(el => { el.style.scrollBehavior = "auto"; el.scrollTop = el.scrollHeight * 0.45; });
  await pg.waitForTimeout(600);
  const btn = pg.locator(".to-bottom");
  console.log(scheme, "hiện nút:", await btn.isVisible(), JSON.stringify(await btn.boundingBox()));
  await pg.screenshot({ path: `${OUT}/scroll-btn-${tag}-${scheme}.png` });
  if (tag === "sau") { await btn.click(); await pg.waitForTimeout(1200); console.log(scheme, "sau khi bấm còn nút:", await btn.isVisible()); }
  await pg.close();
}
await b.close();
