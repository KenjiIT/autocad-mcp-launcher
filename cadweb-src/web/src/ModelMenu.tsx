import { useEffect, useLayoutEffect, useRef, useState } from "react";
import type { ModelInfo } from "./api";

/** "Sonnet 5.5 (cân bằng)" -> { name: "Sonnet 5.5", hint: "cân bằng" } */
const split = (label: string) => {
  const m = /^(.*?)\s*\((.*)\)\s*$/.exec(label);
  return m ? { name: m[1], hint: m[2] } : { name: label, hint: "" };
};

/** Chọn model kiểu Claude: nút chữ nhỏ trong thanh công cụ của ô nhập, bấm mở danh sách phía trên. */
export function ModelMenu({ models, value, onChange, disabled }: { models: ModelInfo[]; value: string; onChange: (id: string) => void; disabled?: boolean }) {
  const [open, setOpen] = useState(false);
  const [hi, setHi] = useState(0);
  const root = useRef<HTMLDivElement>(null);
  const [maxH, setMaxH] = useState(420);
  const cur = models.find(m => m.id === value) ?? models[0];

  // Danh sách mở lên phía trên nút: giới hạn chiều cao theo chỗ còn trống để không bị cắt ở mép trên cửa sổ (Codex có nhiều model).
  useLayoutEffect(() => {
    if (open && root.current) setMaxH(Math.max(160, Math.min(420, root.current.getBoundingClientRect().top - 72)));
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const away = (e: MouseEvent) => { if (!root.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", away);
    return () => document.removeEventListener("mousedown", away);
  }, [open]);

  useEffect(() => { if (open) root.current?.querySelector("li.hi")?.scrollIntoView({ block: "nearest" }); }, [open, hi]);   // chọn bằng phím trong danh sách dài

  if (!cur) return null;
  const pick = (id: string) => { onChange(id); setOpen(false); };
  const key = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") { setOpen(false); return; }
    if (!open && (e.key === "ArrowDown" || e.key === "ArrowUp")) { e.preventDefault(); setHi(models.indexOf(cur)); setOpen(true); return; }
    if (!open) return;
    if (e.key === "ArrowDown") { e.preventDefault(); setHi(i => (i + 1) % models.length); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setHi(i => (i - 1 + models.length) % models.length); }
    else if (e.key === "Enter") { e.preventDefault(); pick(models[hi].id); }
  };

  return (
    <div className="mm" ref={root} onKeyDown={key}>
      <button type="button" className="mm-btn" aria-haspopup="listbox" aria-expanded={open} aria-label={`Model: ${split(cur.label).name}. Bấm để đổi`}
        disabled={disabled} onClick={() => { setHi(models.indexOf(cur)); setOpen(o => !o); }}>
        {split(cur.label).name}
        <svg viewBox="0 0 12 12" aria-hidden="true"><path d="m2.5 4.5 3.5 3.5 3.5-3.5" /></svg>
      </button>
      {open && (
        <ul className="mm-list" role="listbox" aria-label="Chọn model cho phiên này" style={{ maxHeight: maxH, overflowY: "auto" }}>
          {models.map((m, i) => {
            const { name, hint } = split(m.label);
            return (
              <li key={m.id} role="option" aria-selected={m.id === cur.id} className={i === hi ? "hi" : ""}
                onMouseEnter={() => setHi(i)} onMouseDown={e => { e.preventDefault(); pick(m.id); }}>
                <span><b>{name}</b>{hint && <small>{hint}</small>}</span>
                {m.id === cur.id && <svg viewBox="0 0 12 12" aria-hidden="true"><path d="m2.5 6.2 2.4 2.4 4.6-5" /></svg>}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
