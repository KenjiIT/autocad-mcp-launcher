// Thông báo khi agent làm xong hoặc cần người dùng trả lời — chỉ khi người dùng KHÔNG đang nhìn trang.
// Mở trang trên chính máy chạy CAD Studio (localhost): gateway bật thông báo của Windows, không cần trình duyệt
// cấp quyền (Edge hay giấu hộp hỏi quyền). Mở từ máy khác (tunnel): dùng thông báo của trình duyệt.

const KEY = "cad-notify";   // "on" | "off" (mặc định bật)

export const isLocalPage = () => ["localhost", "127.0.0.1", "[::1]", "::1"].includes(location.hostname);
export const notifySupported = () => isLocalPage() || (typeof window !== "undefined" && "Notification" in window);
export const notifyEnabled = () => { try { return localStorage.getItem(KEY) !== "off"; } catch { return true; } };
export const setNotifyEnabled = (on: boolean) => { try { localStorage.setItem(KEY, on ? "on" : "off"); } catch { /* bỏ qua */ } };
/** Bản local không cần quyền của trình duyệt: coi như đã cho phép. */
export const notifyPermission = (): NotificationPermission | "unsupported" =>
  isLocalPage() ? "granted" : "Notification" in window ? Notification.permission : "unsupported";

/** Xin quyền thông báo của trình duyệt (chỉ khi mở từ máy khác). Trình duyệt chỉ cho xin khi người dùng vừa bấm/gõ. */
export async function askNotifyPermission(): Promise<NotificationPermission | "unsupported"> {
  if (isLocalPage()) return "granted";
  if (!("Notification" in window)) return "unsupported";
  if (Notification.permission === "default") { try { await Notification.requestPermission(); } catch { /* bỏ qua */ } }
  return Notification.permission;
}

/** Hiện thông báo nếu đang bật và người dùng không nhìn trang (`force` để thử). */
export function notify(title: string, body: string, opts: { force?: boolean; tag?: string } = {}) {
  if (!notifyEnabled()) return;
  if (!opts.force && document.visibilityState === "visible" && document.hasFocus()) return;
  const text = body.slice(0, 180);
  if (isLocalPage()) {
    void fetch("/api/notify", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ title, body: text, url: location.href }) }).catch(() => {});
    return;
  }
  if (!("Notification" in window) || Notification.permission !== "granted") return;
  try {
    const n = new Notification(title, { body: text, tag: opts.tag });
    n.onclick = () => { window.focus(); n.close(); };
  } catch { /* một số trình duyệt chặn new Notification ngoài service worker: bỏ qua */ }
}
