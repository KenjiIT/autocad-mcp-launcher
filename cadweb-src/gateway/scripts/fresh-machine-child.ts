// Chạy TRONG môi trường giả lập máy mới (do fresh-machine.mjs dựng): gọi đúng các hàm gateway dùng cho Claude CLI.
// Mỗi bước in một dòng JSON {step, ...} để tiến trình cha ghi log.
import { claudeStatus, machineCheck, startInstall, startLogin, claudeBin } from "../src/claudeSetup.ts";

const log = (step: string, data: unknown) => console.log(JSON.stringify({ step, t: new Date().toISOString(), data }));
const sleep = (ms: number) => new Promise(r => setTimeout(r, ms));

const s0 = await claudeStatus();
log("1-status-truoc-cai", s0);
log("2-kiem-tra-may-truoc", await machineCheck());

const started = startInstall();
log("3-bat-dau-cai", started);
const t0 = Date.now();
let st = await claudeStatus();
while (st.installing && Date.now() - t0 < 8 * 60_000) { await sleep(3000); st = await claudeStatus(); }
log("4-status-sau-cai", { ...st, seconds: Math.round((Date.now() - t0) / 1000), bin: claudeBin() });

log("5-mo-dang-nhap", startLogin());
for (let i = 0; i < 3; i++) { await sleep(3000); const s = await claudeStatus(); log(`6-cho-dang-nhap-${i + 1}`, { loggedIn: s.loggedIn, installed: s.installed }); }
log("7-kiem-tra-may-sau", await machineCheck());
