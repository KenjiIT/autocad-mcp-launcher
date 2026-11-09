// Đưa dutoan.db lên kho R2 của cổng để launcher tự tải.
// Dùng:  node tools/upload-dutoan.mjs <đường-dẫn-dutoan.db> [nhãn-phiên-bản]
// Cần: đã `npx wrangler login`, đã tạo bucket `dutoan-data` (xem README).
import { createHash } from "node:crypto";
import { createReadStream, statSync, writeFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";

const [file, label] = process.argv.slice(2);
if (!file) {
  console.error("Cách dùng: node tools/upload-dutoan.mjs <dutoan.db> [nhãn-phiên-bản]");
  process.exit(2);
}
const BUCKET = process.env.DUTOAN_BUCKET || "dutoan-data";

const hash = createHash("sha256");
await new Promise((resolve, reject) =>
  createReadStream(file).on("data", (c) => hash.update(c)).on("end", resolve).on("error", reject));
const manifest = {
  sha256: hash.digest("hex"),
  size: statSync(file).size,
  version: label || new Date().toISOString().slice(0, 10),
};

function put(key, path, type) {
  const r = spawnSync("npx", ["wrangler", "r2", "object", "put", `${BUCKET}/${key}`, "--file", path, "--content-type", type, "--remote"],
    { stdio: "inherit", shell: true });
  if (r.status !== 0) {
    console.error(`Tải ${key} lên không thành công.`);
    process.exit(1);
  }
}

// Tệp dữ liệu trước, manifest sau: máy nào thấy manifest mới thì tệp đã sẵn sàng.
put("dutoan.db", file, "application/octet-stream");
const manifestPath = join(mkdtempSync(join(tmpdir(), "dutoan-")), "manifest.json");
writeFileSync(manifestPath, JSON.stringify(manifest));
put("manifest.json", manifestPath, "application/json");
console.log("Xong:", manifest);
