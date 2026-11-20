import { useEffect, useLayoutEffect, useRef, useState } from "react";
import type { ModelInfo } from "./api";

/** "Claude Opus 5.5 (Cho việc phức tạp)" -> { name: "Claude Opus 5.5", hint: "Cho việc phức tạp" } */
const split = (label: string) => {
  const m = /^(.*?)\s*\((.*)\)\s*$/.exec(label);
  return m ? { name: m[1], hint: m[2] } : { name: label, hint: "" };
};
const short = (name: string) => name.replace(/^Claude\s+/, "");

export const EFFORTS = [
  { id: "low", label: "Thấp" }, { id: "medium", label: "Vừa" }, { id: "high", label: "Cao" },
  { id: "xhigh", label: "Rất cao" }, { id: "max", label: "Tối đa" },
] as const;
export type Effort = typeof EFFORTS[number]["id"];

type Props = {
  models: ModelInfo[]; value: string; onChange: (id: string) => void;
  effort: Effort; onEffort: (e: Effort) => void; disabled?: boolean;
};

/** Chọn model kiểu Claude: ô tìm, danh sách có mô tả, và mức cố gắng ở chân bảng. Mở lên phía trên nút. */
export function ModelMenu({ models, value, onChange, effort, onEffort, disabled }: Props) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [hi, setHi] = useState(0);
  const root = useRef<HTMLDivElement>(null);
  const search = useRef<HTMLInputElement>(null);
  const [maxH, setMaxH] = useState(300);
  const cur = models.find(m => m.id === value) ?? models[0];
  const shown = models.filter(m => m.label.toLowerCase().includes(q.trim().toLowerCase()) || m.id.includes(q.trim().toLowerCase()));

  // Bảng mở lên trên nút: danh sách co theo chỗ trống còn lại để không bị cắt ở mép trên cửa sổ.
  useLayoutEffect(() => {
    if (open && root.current) setMaxH(Math.max(140, Math.min(300, root.current.getBoundingClientRect().top - 170)));
  }, [open]);
  useEffect(() => {
    if (!open) return;
    setQ(""); search.current?.focus();
    const away = (e: MouseEvent) => { if (!root.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", away);
    return () => document.removeEventListener("mousedown", away);
  }, [open]);
  useEffect(() => { setHi(0); }, [q]);
  useEffect(() => { if (open) root.current?.querySelector(".mm-opt.hi")?.scrollIntoView({ block: "nearest" }); }, [open, hi]);

  if (!cur) return null;
  const pick = (id: string) => { onChange(id); setOpen(false); };
  const key = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") { setOpen(false); return; }
    if (!open) return;
    if (e.key === "ArrowDown") { e.preventDefault(); setHi(i => (i + 1) % Math.max(1, shown.length)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setHi(i => (i - 1 + shown.length) % Math.max(1, shown.length)); }
    else if (e.key === "Enter" && shown[hi]) { e.preventDefault(); pick(shown[hi].id); }
  };
  const effLabel = EFFORTS.find(x => x.id === effort)?.label ?? "";

  return (
    <div className="mm" ref={root} onKeyDown={key}>
      <button type="button" className="mm-btn" aria-haspopup="dialog" aria-expanded={open} aria-label={`Model: ${split(cur.label).name}, cố gắng ${effLabel}. Bấm để đổi`}
        disabled={disabled} onClick={() => { setHi(Math.max(0, models.indexOf(cur))); setOpen(o => !o); }}>
        {short(split(cur.label).name)}<span className="mm-eff">· {effLabel}</span>
        <svg viewBox="0 0 12 12" aria-hidden="true"><path d="m2.5 4.5 3.5 3.5 3.5-3.5" /></svg>
      </button>
      {open && (
        <div className="mm-pop" role="dialog" aria-label="Chọn model và mức cố gắng">
          <div className="mm-search">
            <svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="7" cy="7" r="4.5" /><path d="m10.5 10.5 3 3" /></svg>
            <input ref={search} value={q} onChange={e => setQ(e.target.value)} placeholder="Tìm kiếm mô hình…" aria-label="Tìm kiếm mô hình" />
          </div>
          <div className="mm-list" role="listbox" aria-label="Model" style={{ maxHeight: maxH }}>
            {shown.map((m, i) => {
              const { name, hint } = split(m.label);
              const head = m.legacy && !shown[i - 1]?.legacy;   // tiêu đề nhóm ngay trước model đời trước đầu tiên
              return (<div key={m.id} style={{ display: "contents" }}>
                {head && <div className="mm-group" role="presentation">Model đời trước</div>}
                <div role="option" aria-selected={m.id === cur.id} className={`mm-opt${i === hi ? " hi" : ""}${m.id === cur.id ? " on" : ""}`}
                  onMouseEnter={() => setHi(i)} onMouseDown={e => { e.preventDefault(); pick(m.id); }}>
                  <span><b>{name}</b>{hint && <small>{hint}</small>}</span>
                  {m.id === cur.id && <svg viewBox="0 0 12 12" aria-hidden="true"><path d="m2.5 6.2 2.4 2.4 4.6-5" /></svg>}
                </div>
              </div>);
            })}
            {!shown.length && <p className="mm-none">Không có model nào khớp.</p>}
          </div>
          <div className="mm-foot">
            <span>Cố gắng</span>
            <div className="mm-seg" role="radiogroup" aria-label="Mức cố gắng">
              {EFFORTS.map(x => (
                <button key={x.id} type="button" role="radio" aria-checked={effort === x.id} className={effort === x.id ? "on" : ""}
                  onMouseDown={e => e.preventDefault()} onClick={() => onEffort(x.id)}>{x.label}</button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
