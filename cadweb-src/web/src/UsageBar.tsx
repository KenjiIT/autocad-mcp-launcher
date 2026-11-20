import { useEffect, useState } from "react";
import { getPlanUsage, niceError, refreshPlanUsage, type PlanSide, type PlanUsage } from "./api";

/** "1h2m", "2d2h", "45m" — thời gian còn lại tới lúc đặt lại hạn mức. */
const left = (t: number | null) => {
  if (!t) return "";
  const m = Math.max(0, Math.round((t - Date.now()) / 60000));
  const d = Math.floor(m / 1440), h = Math.floor((m % 1440) / 60), mm = m % 60;
  return d ? `${d}d${h}h` : h ? `${h}h${mm}m` : `${mm}m`;
};
const when = (t: number) => new Date(t).toLocaleString("vi-VN", { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "2-digit" });

function Side({ name, s }: { name: string; s: PlanSide }) {
  if (!s) return <span className="ubar-src" title={`Chưa có số của ${name}: dùng ${name} một lượt, hoặc bấm Làm mới.`}><b>{name}</b> —</span>;
  return (
    <span className="ubar-src" title={`${name}${s.plan ? ` · ${s.plan}` : ""} — cập nhật ${when(s.at)}`}>
      <b>{name}</b>{s.plan && <span>{s.plan}</span>}
      {s.windows.map(w => (
        <span key={w.key} className="ubar-win" title={`${w.label}: đã dùng ${w.used}%${w.resetsAt ? ` · đặt lại lúc ${when(w.resetsAt)}` : ""}`}>
          {w.label}
          <span className="ubar-meter"><i className={w.used >= 90 ? "full" : w.used >= 75 ? "warn" : ""} style={{ width: `${Math.min(100, w.used)}%` }} /></span>
          <span className="ubar-num">{w.used}%</span>{w.resetsAt && <span>{left(w.resetsAt)}</span>}
        </span>
      ))}
    </span>
  );
}

/** Thanh "Đã sử dụng" ở đáy trang: hạn mức gói Claude và Codex (giống Orca). Tự tải lại mỗi phút và sau mỗi lượt chat. */
export function UsageBar({ tick }: { tick: number }) {
  const [u, setU] = useState<PlanUsage | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [, setNow] = useState(0);

  useEffect(() => { getPlanUsage().then(setU).catch(e => setErr(niceError(e))); }, [tick]);
  useEffect(() => {
    const t = setInterval(() => { setNow(Date.now()); getPlanUsage().then(setU).catch(() => {}); }, 60_000);
    return () => clearInterval(t);
  }, []);
  const refresh = async () => {
    setBusy(true); setErr("");
    try { setU(await refreshPlanUsage()); } catch (e) { setErr(niceError(e)); } finally { setBusy(false); }
  };

  return (
    <footer className="ubar" aria-label="Hạn mức gói đã sử dụng">
      <span>Đã sử dụng</span>
      <Side name="Claude" s={u?.claude ?? null} />
      <span className="ubar-sep" aria-hidden="true" />
      <Side name="Codex" s={u?.codex ?? null} />
      {err && <span className="err-msg">{err}</span>}
      <button type="button" className="ghost" disabled={busy} onClick={() => void refresh()}
        title="Lấy số mới của Claude ngay (gửi một câu rất ngắn bằng Haiku, có tính vào gói)">{busy ? "Đang lấy…" : "↻ Làm mới"}</button>
    </footer>
  );
}
