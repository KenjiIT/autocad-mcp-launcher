// Playwright: hộp Xóa dự án — không tick / tick + gõ OK (chấp nhận OK|confirm, không phân biệt hoa thường), Enter trong ô gửi lệnh xóa.
// API xóa được giả lập (không xóa thật). Chạy khi CAD Studio mở ở http://localhost:5176: node scripts/e2e/delete-project.mjs <thư mục ảnh>
import { chromium } from "playwright-core";
const OUT = process.argv[2] ?? ".";
const b = await chromium.launch({ executablePath: "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" });
for (const scheme of ["light", "dark"]) {
  const pg = await b.newPage({ viewport: { width: 1280, height: 820 }, colorScheme: scheme });
  await pg.route("**/delete-info", r => r.fulfill({ json: { dir: ["C:", "Users", "minhk", "CAD Studio", "projects", "vẽ nhà"].join(String.fromCharCode(92)), exists: true, files: 47, bytes: 18_400_000, capped: false, folderProblem: null } }));
  let deletes = 0;
  await pg.route(/\/api\/projects\/[^/]+(\?.*)?$/, r => r.request().method() === "DELETE" ? (deletes++, r.fulfill({ status: 500, json: { error: "chụp ảnh: không xóa thật" } })) : r.continue());
  await pg.goto("http://localhost:5176/"); await pg.waitForSelector(".prow"); await pg.waitForTimeout(1200);
  const row = pg.locator(".prow").filter({ hasText: "vẽ nhà" }).first();
  await row.click({ button: "right" }); await pg.waitForTimeout(300);
  await pg.locator("[role=menuitem]").filter({ hasText: "Xóa dự án khỏi CAD Studio" }).click();
  await pg.waitForSelector("dialog.ddlg[open] .ddlg-dir small:has-text('file')"); await pg.waitForTimeout(400);
  const box = pg.locator("dialog.ddlg");
  await box.screenshot({ path: `${OUT}/sau-xoa-du-an-khong-tick-${scheme}.png` });
  await pg.locator(".ddlg-check input").check();
  const btn = pg.locator("dialog.ddlg button[type=submit]");
  console.log(scheme, "nút sau khi tick:", await btn.innerText(), "bật?", await btn.isEnabled());
  const input = pg.locator("#ddlg-name");
  for (const v of ["vẽ nhà", "oke", " Confirm ", " ok "]) { await input.fill(v); console.log(scheme, JSON.stringify(v), "-> bật?", await btn.isEnabled()); }
  await input.fill("OK"); await pg.waitForTimeout(200);
  await box.screenshot({ path: `${OUT}/sau-xoa-du-an-tick-${scheme}.png` });
  await input.press("Enter"); await pg.waitForTimeout(600);
  console.log(scheme, "Enter gửi lệnh xóa:", deletes === 1, "| báo:", await pg.locator("dialog.ddlg .err-msg").innerText().catch(() => ""));
  await pg.close();
}
await b.close();
