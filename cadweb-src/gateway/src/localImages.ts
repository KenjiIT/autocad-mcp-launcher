import { existsSync, readFileSync, realpathSync, statSync } from "node:fs";
import { join, resolve, sep } from "node:path";

// Một số tool CAD (vd. view/get_screenshot) chỉ trả ĐƯỜNG DẪN file ảnh trên máy CAD, không trả nội dung ảnh.
// Nếu gateway chạy cùng máy, đọc file đó và đính thành ảnh để web hiển thị. Chỉ đọc trong thư mục cho phép.
const MIME: Record<string, string> = { png: "image/png", jpg: "image/jpeg", jpeg: "image/jpeg", webp: "image/webp" };
const MAX_BYTES = 3.5 * 1024 * 1024; // base64 phình ~33%, API nhận ảnh tối đa 5 MB
const MAX_IMAGES = 4;

/** CAD_IMAGE_ROOTS: các thư mục cho phép, ngăn cách bằng ";". Mặc định: thư mục cài AutoCAD MCP Launcher. */
export const roots = () => (process.env.CAD_IMAGE_ROOTS?.split(";").map(s => s.trim()).filter(Boolean)
  ?? [join(process.env.LOCALAPPDATA ?? "", "Programs", "AutoCAD MCP Launcher")])
  .flatMap(r => { try { return [realpathSync(resolve(r))]; } catch { return []; } });

const PATH_RE = /[A-Za-z]:[\\/][^"<>|*?\r\n]*?\.(?:png|jpe?g|webp)\b/gi;

export function attachLocalImages(content: any[] | undefined): any[] | undefined {
  if (!content) return content;
  const allowed = roots();
  if (!allowed.length) return content;
  const seen = new Set<string>(), extra: any[] = [];
  for (const c of content) {
    if (c.type !== "text" || typeof c.text !== "string") continue;
    for (const m of c.text.matchAll(PATH_RE)) {
      if (extra.length >= MAX_IMAGES) break;
      try {
        const raw = m[0].replace(/\\\\/g, "\\");          // JSON thoát ký tự "\"
        if (!existsSync(raw)) continue;
        const real = realpathSync(raw);                   // chống symlink/.. thoát khỏi thư mục cho phép
        if (seen.has(real) || !allowed.some(r => real === r || real.startsWith(r + sep))) continue;
        const st = statSync(real);
        if (!st.isFile() || st.size > MAX_BYTES) continue;
        seen.add(real);
        extra.push({ type: "image", mimeType: MIME[real.split(".").pop()!.toLowerCase()], data: readFileSync(real).toString("base64") });
      } catch (e) { if (process.env.DEBUG_IMG) console.error("img:", String(e)); }
    }
  }
  return extra.length ? [...content, ...extra] : content;
}
