// Hình do agent vẽ trong chat: khối ```svg và file ảnh (.svg/.png/.jpg) agent ghi trong thư mục dự án rồi nhắc đường dẫn.
// SVG được làm sạch (bỏ script, on*, foreignObject, liên kết ngoài) rồi hiện bằng <img src="data:..."> — trình duyệt không chạy
// script hay tải tài nguyên ngoài của SVG nạp qua <img>, nên đây là hai lớp chặn. Tách riêng (không React) để kiểm thử.

export const SVG_MAX = 400_000;   // ký tự; hình lớn hơn coi như không hợp lệ

const DANGEROUS = ["script", "foreignObject", "iframe", "object", "embed", "audio", "video", "handler", "listener"];

/** Làm sạch một SVG do agent viết. Không phải SVG hoặc quá lớn thì null. */
export function sanitizeSvg(src: string): string | null {
  let s = (src ?? "").trim();
  if (!s || s.length > SVG_MAX) return null;
  s = s.replace(/<\?xml[\s\S]*?\?>/gi, "").replace(/<!DOCTYPE[\s\S]*?>/gi, "").replace(/<!--[\s\S]*?-->/g, "").trim();
  if (!/^<svg[\s>]/i.test(s) || !/<\/svg>\s*$/i.test(s)) return null;
  // Thẻ nguy hiểm: bỏ cả nội dung, rồi bỏ thẻ mở/đóng lẻ còn sót
  for (const tag of DANGEROUS) {
    s = s.replace(new RegExp(`<${tag}\\b[\\s\\S]*?<\\/${tag}\\s*>`, "gi"), "");
    s = s.replace(new RegExp(`<\\/?${tag}\\b[^>]*>`, "gi"), "");
  }
  // Thuộc tính sự kiện on*=
  s = s.replace(/\s+on[a-z]+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi, "");
  // href / xlink:href / src chỉ được trỏ trong chính hình (#id)
  s = s.replace(/\s+(?:xlink:)?(?:href|src)\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi, (m, v: string) => /^["']?#/.test(v) ? m : "");
  // url(...) trong style chỉ cho #id
  s = s.replace(/url\(\s*(['"]?)(?!#)[^)]*\)/gi, "none");
  s = s.replace(/javascript:/gi, "");
  if (!/<svg[^>]*\sxmlns=/i.test(s)) s = s.replace(/^<svg/i, '<svg xmlns="http://www.w3.org/2000/svg"');
  return s;
}

/** data URL để hiện SVG đã làm sạch trong <img>. */
export const svgDataUrl = (clean: string) => `data:image/svg+xml;charset=utf-8,${encodeURIComponent(clean)}`;

const IMG_EXT = /\.(svg|png|jpe?g|webp|gif)$/i;
const norm = (p: string) => p.replace(/\\/g, "/").replace(/\/+$/, "");

/**
 * Đường dẫn ảnh agent nhắc tới trong tin, quy về đường dẫn TƯƠNG ĐỐI trong thư mục dự án (để gọi /api/projects/:id/raw).
 * Nhận đường dẫn tuyệt đối nằm trong thư mục dự án và đường dẫn tương đối; bỏ URL, đường dẫn ra ngoài dự án và "..".
 */
export function imageRefs(text: string, projectDir: string | null | undefined): string[] {
  if (!projectDir) return [];
  const dir = norm(projectDir);
  const found: string[] = [];
  for (const m of text.matchAll(/`([^`\n]+)`/g)) found.push(m[1].trim());   // trong `...` (có thể có dấu cách)
  const plain = text.replace(/`[^`\n]+`/g, " ");   // phần ngoài `...`: đường dẫn không có dấu cách
  for (const m of plain.matchAll(/(?:[A-Za-z]:[\\/])?[^\s`'"<>|*?()[\]]+\.(?:svg|png|jpe?g|webp|gif)\b/gi)) found.push(m[0]);
  const out: string[] = [];
  for (let raw of found) {
    raw = raw.replace(/^["'(<]+|[)"'>.,;:]+$/g, "");
    if (!IMG_EXT.test(raw) || /^[a-z]+:\/\//i.test(raw) || raw.startsWith("data:")) continue;
    let p = norm(raw);
    if (/^[A-Za-z]:\//.test(p) || p.startsWith("/")) {
      if (!p.toLowerCase().startsWith(dir.toLowerCase() + "/")) continue;
      p = p.slice(dir.length + 1);
    }
    p = p.replace(/^\.\//, "");
    if (!p || p.split("/").includes("..")) continue;
    if (!out.includes(p)) out.push(p);
  }
  return out;
}
