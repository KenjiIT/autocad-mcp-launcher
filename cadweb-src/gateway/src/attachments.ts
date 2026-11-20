import { mkdtempSync, realpathSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

// Ảnh người dùng dán/đính vào tin nhắn. Dữ liệu đến từ trình duyệt nên KHÔNG tin: kiểm loại, kích thước và chữ ký file trước khi dùng.
export const MAX_IMAGES = 4;
const MAX_B64 = 7_000_000;                 // ~5 MB sau khi giải mã (giới hạn ảnh của API Claude)
const EXT: Record<string, string> = { "image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "image/gif": "gif" };

export type UserImage = { mime: string; data: string };
export class AttachmentError extends Error {}

/** Đầu file có đúng là loại ảnh khai báo không (chặn việc gửi file lạ đội lốt ảnh). */
function magicOk(mime: string, b64: string): boolean {
  const h = Buffer.from(b64.slice(0, 24), "base64");
  if (mime === "image/png") return h.subarray(0, 4).equals(Buffer.from([0x89, 0x50, 0x4e, 0x47]));
  if (mime === "image/jpeg") return h.subarray(0, 3).equals(Buffer.from([0xff, 0xd8, 0xff]));
  if (mime === "image/gif") return h.subarray(0, 4).toString("latin1") === "GIF8";
  if (mime === "image/webp") return h.subarray(0, 4).toString("latin1") === "RIFF" && Buffer.from(b64.slice(0, 24), "base64").subarray(8, 12).toString("latin1") === "WEBP";
  return false;
}

/** Tách nội dung tin nhắn người dùng (chuỗi, hoặc mảng block kiểu Anthropic) thành chữ và ảnh đã kiểm. */
export function splitContent(content: unknown): { text: string; images: UserImage[] } {
  if (typeof content === "string") return { text: content, images: [] };
  if (!Array.isArray(content)) return { text: "", images: [] };
  let text = "";
  const images: UserImage[] = [];
  for (const b of content as any[]) {
    if (b?.type === "text" && typeof b.text === "string") text += (text ? "\n" : "") + b.text;
    else if (b?.type === "image") {
      const mime = b.source?.media_type, data = b.source?.data;
      if (b.source?.type !== "base64" || typeof mime !== "string" || !EXT[mime]) throw new AttachmentError("Chỉ nhận ảnh PNG, JPEG, WebP hoặc GIF.");
      if (typeof data !== "string" || !/^[A-Za-z0-9+/]+={0,2}$/.test(data) || data.length > MAX_B64) throw new AttachmentError("Ảnh không hợp lệ hoặc quá lớn (tối đa khoảng 5 MB mỗi ảnh).");
      if (!magicOk(mime, data)) throw new AttachmentError("Nội dung file không khớp với loại ảnh khai báo.");
      images.push({ mime, data });
    }
  }
  if (images.length > MAX_IMAGES) throw new AttachmentError(`Tối đa ${MAX_IMAGES} ảnh mỗi tin nhắn.`);
  return { text, images };
}

/** Chế độ API: dựng lại nội dung CHỈ từ các block đã kiểm (ảnh trước, chữ sau). */
export function rebuildContent(text: string, images: UserImage[]): string | unknown[] {
  if (!images.length) return text;
  return [
    ...images.map(i => ({ type: "image", source: { type: "base64", media_type: i.mime, data: i.data } })),
    { type: "text", text: text || "Hãy xem ảnh đính kèm." },
  ];
}

export type Staged = { dir: string; files: string[]; cleanup: () => void };

/** Chế độ CLI/Codex: ghi ảnh ra thư mục tạm riêng của lượt chat (chỉ chủ tiến trình đọc được), xóa khi xong. */
export function stage(images: UserImage[]): Staged | undefined {
  if (!images.length) return undefined;
  const dir = realpathSync(mkdtempSync(join(tmpdir(), "cad-web-att-")));
  const files = images.map((im, i) => {
    const f = join(dir, `anh-${i + 1}.${EXT[im.mime]}`);
    writeFileSync(f, Buffer.from(im.data, "base64"), { mode: 0o600 });
    return f;
  });
  return { dir, files, cleanup: () => { try { rmSync(dir, { recursive: true, force: true }); } catch { /* dọn tạm, bỏ qua */ } } };
}
