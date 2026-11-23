import { useCallback, useEffect, useRef, useState } from "react";
import { getCliUpdates, niceError, updateCli, type CliInfo } from "./api";

const ICON: Record<string, string> = { claude: "✳", codex: "◎" };

/** Chỉ báo "CLI updates" ở thanh đáy + bảng popover (giống Orca). Kiểm tra khi mở app và mỗi 6 giờ; khi đang cập nhật thì hỏi lại mỗi 1,5 giây. */
export function CliUpdates() {
  const [list, setList] = useState<CliInfo[] | null>(null);
  const [open, setOpen] = useState(false);
  const [err, setErr] = useState("");
  const [checking, setChecking] = useState(false);
  const box = useRef<HTMLDivElement>(null);

  const load = useCallback(async (force = false) => {
    if (force) setChecking(true);
    try { setList(await getCliUpdates(force)); setErr(""); } catch (e) { setErr(niceError(e)); } finally { setChecking(false); }
  }, []);
  useEffect(() => { void load(); const t = setInterval(() => void load(), 6 * 3600_000); return () => clearInterval(t); }, [load]);
  const busy = !!list?.some(c => c.updating);
  useEffect(() => { if (!busy) return; const t = setInterval(() => void load(), 1500); return () => clearInterval(t); }, [busy, load]);
  useEffect(() => {
    if (!open) return;
    const h = (e: MouseEvent) => { if (!box.current?.contains(e.target as Node)) setOpen(false); };
    const k = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", h); document.addEventListener("keydown", k);
    return () => { document.removeEventListener("mousedown", h); document.removeEventListener("keydown", k); };
  }, [open]);

  const run = async (ids: string[]) => {
    setErr("");
    for (const id of ids) { try { await updateCli(id); } catch (e) { setErr(niceError(e)); } }
    await load();
  };

  const avail = list?.filter(c => c.updateAvailable) ?? [];
  const todo = avail.filter(c => c.canUpdate && !c.updating);
  const label = busy ? "Updating CLIs" : avail.length ? `${avail.length} CLI update${avail.length > 1 ? "s" : ""}` : "CLIs up to date";

  return (
    <div className="cliu" ref={box}>
      <button type="button" className={`ghost cliu-chip${avail.length || busy ? " on" : ""}`} onClick={() => setOpen(o => !o)}
        aria-expanded={open} title="Phiên bản các CLI mà gateway dùng">
        {busy ? <span className="spin" aria-hidden="true" /> : <span className="cliu-dot" aria-hidden="true" />}{label}
      </button>
      {open && (
        <div className="cliu-pop" role="dialog" aria-label="Cập nhật CLI">
          <div className="cliu-head">
            <b>{avail.length ? `${avail.length} CLI update${avail.length > 1 ? "s" : ""} available` : "Tất cả CLI đã là bản mới nhất"}</b>
            {todo.length > 0 && <button type="button" onClick={() => void run(todo.map(c => c.id))}>Update all</button>}
          </div>
          {!list && !err && <p className="cliu-note">Đang kiểm tra…</p>}
          {list?.map(c => (
            <div key={c.id} className="cliu-row">
              <span className="cliu-ico" aria-hidden="true">{ICON[c.id] ?? "▸"}</span>
              <div className="cliu-main">
                <b>{c.name}</b>
                <span className="cliu-ver">{c.installed ?? "chưa cài"}{c.latest && c.installed && c.updateAvailable ? <> → <em>{c.latest}</em></> : c.latest ? " · mới nhất" : ""}</span>
                {c.updating && c.progress && <span className="cliu-note">{c.progress}</span>}
                {c.error && <span className="err-msg">{c.error}</span>}
                {c.updateAvailable && !c.canUpdate && c.hint && <span className="cliu-note">{c.hint}</span>}
              </div>
              {c.updating ? <span className="cliu-busy"><span className="spin" aria-hidden="true" />Updating...</span>
                : c.updateAvailable && c.canUpdate ? <button type="button" onClick={() => void run([c.id])}>Update</button> : null}
            </div>
          ))}
          {err && <p className="err-msg">{err}</p>}
          <div className="cliu-foot">
            <button type="button" className="ghost" disabled={checking} onClick={() => void load(true)}>{checking ? "Đang kiểm tra…" : "↻ Kiểm tra lại"}</button>
          </div>
        </div>
      )}
    </div>
  );
}
