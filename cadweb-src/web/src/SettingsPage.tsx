import { useEffect, useRef, useState } from "react";
import { Settings } from "./Settings";
import { askNotifyPermission, isLocalPage, notify, notifyEnabled, notifyPermission, notifySupported, setNotifyEnabled } from "./notify";
import { LocalMcp } from "./LocalMcp";
import { getClickAction, getPlanUsage, niceError, refreshPlanUsage, setClickAction, type ClickAction, type PlanSide, type PlanUsage } from "./api";

type Item = { id: string; label: string; icon: string; keys: string };
const GROUPS: { title: string; items: Item[] }[] = [
  { title: "Khả năng AI", items: [
    { id: "ai", label: "Trợ lý AI", icon: "✦", keys: "claude cli codex api key cách gọi engine đăng nhập cài đặt claude model" },
  ] },
  { title: "Dự án", items: [
    { id: "files", label: "Mở file", icon: "▤", keys: "mở file bấm click ứng dụng app mặc định autocad excel word web trình duyệt mở bằng" },
    { id: "notify", label: "Thông báo", icon: "◉", keys: "thông báo popup notification xong hoàn thành báo agent hỏi windows" },
  ] },
  { title: "Kết nối", items: [
    { id: "mcp", label: "MCP trên máy này", icon: "⇄", keys: "mcp autocad beiming puran dự toán dutoan launcher 8764 server tool" },
  ] },
  { title: "Tài khoản", items: [
    { id: "plan", label: "Hạn mức gói", icon: "◔", keys: "hạn mức gói sử dụng usage giới hạn 5h tuần max plus claude codex token" },
  ] },
];
const ALL = GROUPS.flatMap(g => g.items);

/** Trang Cài đặt kiểu Orca: cột trái (ô tìm + các nhóm mục), bên phải là nội dung của mục đang chọn. */
export function SettingsPage({ reloadKey, onSaved, onMcpChanged }: { reloadKey: string; onSaved: () => void; onMcpChanged: () => void }) {
  const [sel, setSel] = useState(() => { try { return sessionStorage.getItem("cad-settings") || "ai"; } catch { return "ai"; } });
  const [q, setQ] = useState("");
  const search = useRef<HTMLInputElement>(null);
  const pick = (id: string) => { setSel(id); try { sessionStorage.setItem("cad-settings", id); } catch { /* bỏ qua */ } };

  // Ctrl+F khi đang ở trang Cài đặt: nhảy vào ô tìm (như Orca), không mở ô tìm của trình duyệt.
  useEffect(() => {
    const key = (e: KeyboardEvent) => { if (e.ctrlKey && e.key.toLowerCase() === "f") { e.preventDefault(); search.current?.focus(); search.current?.select(); } };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, []);

  const needle = q.trim().toLowerCase();
  const match = (it: Item) => !needle || (it.label + " " + it.keys).toLowerCase().includes(needle);
  const cur = ALL.find(i => i.id === sel) ?? ALL[0];

  return (
    <div className="full sp">
      <nav className="sp-nav" aria-label="Mục cài đặt">
        <label className="sp-search">
          <svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="7" cy="7" r="4.5" /><path d="m10.5 10.5 3 3" /></svg>
          <input ref={search} value={q} onChange={e => setQ(e.target.value)} placeholder="Tìm cài đặt" aria-label="Tìm cài đặt"
            onKeyDown={e => { if (e.key === "Enter") { const first = ALL.find(match); if (first) pick(first.id); } if (e.key === "Escape") setQ(""); }} />
          <kbd>Ctrl</kbd><kbd>F</kbd>
        </label>
        {GROUPS.map(g => {
          const items = g.items.filter(match);
          return items.length ? (
            <div key={g.title} className="sp-group">
              <div className="sp-gtitle">{g.title}</div>
              {items.map(it => (
                <button key={it.id} type="button" className={`sp-item${it.id === cur.id ? " on" : ""}`} aria-current={it.id === cur.id ? "page" : undefined} onClick={() => pick(it.id)}>
                  <span className="sp-ic" aria-hidden="true">{it.icon}</span>{it.label}
                </button>
              ))}
            </div>
          ) : null;
        })}
        {!ALL.some(match) && <p className="sp-none">Không có mục nào khớp “{q}”.</p>}
      </nav>
      <section className="sp-body" aria-labelledby="sp-title">
        <div className="sp-inner">
          <h1 id="sp-title">{cur.label}</h1>
          {cur.id === "ai" && <Settings onSaved={onSaved} reloadKey={reloadKey} />}
          {cur.id === "mcp" && <LocalMcp onChanged={onMcpChanged} />}
          {cur.id === "plan" && <PlanDetail />}
          {cur.id === "files" && <FileClick />}
          {cur.id === "notify" && <NotifySettings />}
        </div>
      </section>
    </div>
  );
}

const when = (t: number) => new Date(t).toLocaleString("vi-VN", { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "2-digit" });

function PlanCard({ name, s }: { name: string; s: PlanSide }) {
  return (
    <div className="sp-card">
      <div className="sp-card-head"><b>{name}</b>{s?.plan && <span className="badge">{s.plan}</span>}
        {s && <small>cập nhật {when(s.at)}</small>}</div>
      {!s ? <p className="help">Chưa có số. Dùng {name} một lượt chat{name === "Claude" ? ", hoặc bấm Làm mới" : ""}.</p>
        : s.windows.map(w => (
          <div key={w.key} className="sp-win">
            <span className="sp-win-l">{w.label === "5h" ? "Khung 5 giờ" : w.label === "tuần" ? "Khung 7 ngày" : w.label}</span>
            <span className="sp-bar"><i className={w.used >= 90 ? "full" : w.used >= 75 ? "warn" : ""} style={{ width: `${Math.min(100, w.used)}%` }} /></span>
            <span className="sp-win-n">{w.used}%</span>
            <small>{w.resetsAt ? `đặt lại ${when(w.resetsAt)}` : "chưa dùng trong khung này"}</small>
          </div>
        ))}
    </div>
  );
}

/** Chi tiết hạn mức gói (cùng nguồn với thanh "Đã sử dụng" ở đáy trang). */
function PlanDetail() {
  const [u, setU] = useState<PlanUsage | null>(null);
  const [busy, setBusy] = useState(false); const [err, setErr] = useState("");
  useEffect(() => { getPlanUsage().then(setU).catch(e => setErr(niceError(e))); }, []);
  const refresh = async () => { setBusy(true); setErr(""); try { setU(await refreshPlanUsage()); } catch (e) { setErr(niceError(e)); } finally { setBusy(false); } };
  return (
    <div className="sp-plan">
      <p className="help">Hạn mức của gói tài khoản đang đăng nhập trên máy này (Claude Pro/Max, gói ChatGPT cho Codex). Số của Claude cập nhật sau mỗi lượt chat; Codex lấy từ nhật ký phiên của Codex.</p>
      <PlanCard name="Claude" s={u?.claude ?? null} />
      <PlanCard name="Codex" s={u?.codex ?? null} />
      {err && <p className="err-msg" role="alert">{err}</p>}
      <div><button type="button" disabled={busy} onClick={() => void refresh()}>{busy ? "Đang lấy…" : "Làm mới số của Claude"}</button>
        <p className="help">Gửi một câu rất ngắn bằng Haiku để Claude trả số mới (có tính vào gói).</p></div>
    </div>
  );
}

/** Bấm vào file ở cột file thì làm gì — do người dùng chọn. */
function FileClick() {
  const [v, setV] = useState<ClickAction>(getClickAction);
  const pick = (x: ClickAction) => { setV(x); setClickAction(x); };
  const opts: [ClickAction, string, string][] = [
    ["default", "Mở bằng ứng dụng mặc định của Windows", "DWG/DXF mở bằng AutoCAD, XLSX bằng Excel, DOCX bằng Word… theo cài đặt \"Mở bằng\" của Windows."],
    ["choose", "Hỏi chọn ứng dụng mỗi lần", "Hiện hộp \"Mở bằng\" của Windows để chọn app; có thể tick \"Luôn dùng ứng dụng này\" cho loại file đó."],
    ["web", "Xem trên web (tab mới)", "Ảnh, PDF, TXT, MD, CSV, JSON xem ngay trên trình duyệt; loại file khác vẫn mở bằng ứng dụng mặc định."],
  ];
  return (
    <div className="sp-form">
      <fieldset className="engine">
        <legend>Khi bấm vào một file ở cột file</legend>
        {opts.map(([id, label, help]) => (
          <label key={id} className="opt"><input type="radio" name="file-click" checked={v === id} onChange={() => pick(id)} />
            <span><b>{label}</b><small>{help}</small></span></label>
        ))}
      </fieldset>
      <p className="help">Chuột phải vào file luôn có đủ các cách mở (Mở bằng › Trình duyệt / Ứng dụng mặc định / Chọn ứng dụng…). Lựa chọn này lưu trên trình duyệt đang dùng.</p>
    </div>
  );
}

/** Bật/tắt thông báo khi agent xong hoặc cần trả lời, xin quyền của trình duyệt và gửi thử. */
function NotifySettings() {
  const [on, setOn] = useState(notifyEnabled);
  const [perm, setPerm] = useState(notifyPermission);
  const toggle = (v: boolean) => { setOn(v); setNotifyEnabled(v); };
  const allow = async () => setPerm(await askNotifyPermission());
  const test = async () => { const p = await askNotifyPermission(); setPerm(p); notify("CAD Studio: thông báo thử", "Thông báo sẽ hiện như thế này khi agent làm xong.", { force: true }); };
  const permText = isLocalPage() ? "Đang mở trên chính máy này: thông báo hiện bằng thông báo của Windows, không cần trình duyệt cho phép."
    : perm === "granted" ? "Trình duyệt đã cho phép." : perm === "denied"
    ? "Trình duyệt đang CHẶN thông báo của trang này. Bấm biểu tượng ổ khóa cạnh địa chỉ trang → Quyền → Thông báo → Cho phép, rồi tải lại trang."
    : perm === "unsupported" ? "Trình duyệt này không hỗ trợ thông báo." : "Chưa cho phép: bấm \"Cho phép thông báo\" (hoặc trình duyệt sẽ hỏi lần đầu bạn gửi tin).";
  return (
    <div className="sp-form">
      <label className="opt"><input type="checkbox" checked={on} onChange={e => toggle(e.target.checked)} />
        <span><b>Báo khi agent làm xong hoặc cần bạn trả lời</b>
          <small>Hiện thông báo của Windows (góc màn hình) khi bạn đang ở tab hoặc cửa sổ khác. Đang xem CAD Studio thì không báo.</small></span></label>
      <p className="help">{permText}</p>
      {notifySupported() && <div className="sp-btns">
        {perm !== "granted" && perm !== "denied" && <button type="button" className="primary" onClick={() => void allow()}>Cho phép thông báo</button>}
        <button type="button" disabled={perm === "denied" || !on} onClick={() => void test()}>Gửi thử</button>
      </div>}
    </div>
  );
}
