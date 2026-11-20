// Ảnh người dùng dán/kéo thả/chọn vào khung chat. Thu nhỏ trước khi gửi: nhẹ cho đường truyền, rẻ token, và gateway chỉ nhận tối đa ~5 MB mỗi ảnh.
export type Att = { id: string; mime: string; data: string; preview: string };

export const MAX_IMAGES = 4;
const MAX_SIDE = 1568;                 // cạnh dài hơn mức này Claude cũng tự thu nhỏ, gửi dư chỉ tốn băng thông
const MAX_BYTES = 3 * 1024 * 1024;
const OK = ["image/png", "image/jpeg", "image/webp", "image/gif"];

const toBase64 = (b: Blob) => new Promise<string>((res, rej) => {
  const r = new FileReader();
  r.onload = () => res(String(r.result).split(",")[1] ?? "");
  r.onerror = () => rej(new Error("Không đọc được ảnh."));
  r.readAsDataURL(b);
});
const encode = (cv: HTMLCanvasElement, type: string, q?: number) => new Promise<Blob | null>(res => cv.toBlob(res, type, q));

export async function prepareImage(file: File): Promise<Att> {
  if (!OK.includes(file.type)) throw new Error(`"${file.name || "ảnh"}": chỉ nhận PNG, JPEG, WebP hoặc GIF.`);
  let blob: Blob = file, mime = file.type;
  if (mime === "image/gif") {
    if (file.size > MAX_BYTES) throw new Error("Ảnh GIF quá lớn (tối đa 3 MB).");
  } else {
    const bmp = await createImageBitmap(file).catch(() => { throw new Error("Không mở được ảnh này."); });
    const k = Math.min(1, MAX_SIDE / Math.max(bmp.width, bmp.height));
    if (k < 1 || file.size > MAX_BYTES) {
      const cv = document.createElement("canvas");
      cv.width = Math.max(1, Math.round(bmp.width * k)); cv.height = Math.max(1, Math.round(bmp.height * k));
      const g = cv.getContext("2d")!;
      g.drawImage(bmp, 0, 0, cv.width, cv.height);
      let out = mime === "image/png" ? await encode(cv, "image/png") : null;       // ảnh chụp màn hình giữ PNG cho chữ nét
      if (out && out.size <= MAX_BYTES) mime = "image/png";
      else {
        g.globalCompositeOperation = "destination-over"; g.fillStyle = "#fff"; g.fillRect(0, 0, cv.width, cv.height);   // JPEG không có nền trong suốt
        out = await encode(cv, "image/jpeg", 0.88); mime = "image/jpeg";
      }
      if (!out || out.size > MAX_BYTES) throw new Error("Ảnh quá lớn, hãy thử ảnh nhỏ hơn.");
      blob = out;
    }
    bmp.close();
  }
  return { id: crypto.randomUUID?.() ?? String(Math.random()), mime, data: await toBase64(blob), preview: URL.createObjectURL(blob) };
}
