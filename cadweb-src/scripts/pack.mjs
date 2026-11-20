// Đóng gói cad-web-local để chạy kèm AutoCAD MCP Launcher, không cần npm install trên máy người dùng:
//   <out>/web/          web đã build (Vite)
//   <out>/gateway/      server.mjs + ask-mcp.mjs, mỗi file đã gộp sẵn thư viện (esbuild)
// Chạy: node scripts/pack.mjs <thư mục ra>   (cần npm install trước, ở máy build)
import { build } from "esbuild";
import { execSync } from "node:child_process";
import { cpSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const here = resolve(import.meta.dirname, "..");
const out = resolve(process.argv[2] ?? resolve(here, "dist-pack"));
rmSync(out, { recursive: true, force: true });
mkdirSync(resolve(out, "gateway"), { recursive: true });

execSync("npm run build -w web", { cwd: here, stdio: "inherit" });
cpSync(resolve(here, "web", "dist"), resolve(out, "web"), { recursive: true });

const common = {
  bundle: true, platform: "node", format: "esm", target: "node22", logLevel: "warning",
  // Vài thư viện CommonJS cần require() khi đã gộp vào ESM.
  banner: { js: "import { createRequire as __cr } from 'node:module'; const require = __cr(import.meta.url);" },
};
await build({ ...common, entryPoints: [resolve(here, "gateway/src/index.ts")], outfile: resolve(out, "gateway/server.mjs") });
await build({ ...common, entryPoints: [resolve(here, "gateway/src/ask-mcp.mjs")], outfile: resolve(out, "gateway/ask-mcp.mjs") });
writeFileSync(resolve(out, "gateway/package.json"), JSON.stringify({ type: "module" }));
console.log(out);
