import { useEffect, useLayoutEffect, useRef, useState } from "react";

export type MenuItem =
  | { sep: true }
  | { label: string; icon?: string; hint?: string; danger?: boolean; disabled?: boolean; onClick?: () => void; sub?: MenuItem[] };

/** Menu chuột phải kiểu Orca: mở tại vị trí chuột, có menu con, đóng khi bấm ra ngoài / Esc / cuộn / đổi cỡ cửa sổ. */
export function ContextMenu({ x, y, items, onClose }: { x: number; y: number; items: MenuItem[]; onClose: () => void }) {
  useEffect(() => {
    const close = (e: Event) => { if (!(e.target as HTMLElement)?.closest?.(".cmenu")) onClose(); };
    const key = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    const away = () => onClose();
    document.addEventListener("mousedown", close, true);
    document.addEventListener("contextmenu", close, true);
    document.addEventListener("keydown", key);
    window.addEventListener("resize", away);
    window.addEventListener("blur", away);
    document.addEventListener("scroll", away, true);
    return () => {
      document.removeEventListener("mousedown", close, true);
      document.removeEventListener("contextmenu", close, true);
      document.removeEventListener("keydown", key);
      window.removeEventListener("resize", away);
      window.removeEventListener("blur", away);
      document.removeEventListener("scroll", away, true);
    };
  }, [onClose]);
  return <Panel x={x} y={y} items={items} onClose={onClose} root />;
}

function Panel({ x, y, items, onClose, root, flipFrom }: { x: number; y: number; items: MenuItem[]; onClose: () => void; root?: boolean; flipFrom?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState({ left: x, top: y });
  const [sub, setSub] = useState<{ i: number; x: number; y: number; left: number } | null>(null);
  useLayoutEffect(() => {   // giữ menu trong cửa sổ: tràn phải thì lật sang trái, tràn dưới thì đẩy lên
    const r = ref.current!.getBoundingClientRect();
    let left = x, top = y;
    if (left + r.width > innerWidth - 4) left = flipFrom !== undefined ? flipFrom - r.width : innerWidth - r.width - 4;
    if (top + r.height > innerHeight - 4) top = Math.max(4, innerHeight - r.height - 4);
    setPos({ left: Math.max(4, left), top });
  }, [x, y]);
  useEffect(() => { if (root) ref.current?.querySelector<HTMLButtonElement>("button:not(:disabled)")?.focus(); }, []);

  const hover = (el: HTMLElement, i: number, has: boolean) => {
    if (!has) { setSub(null); return; }
    const r = el.getBoundingClientRect();
    setSub({ i, x: r.right - 2, y: r.top - 5, left: r.left + 2 });
  };
  const move = (e: React.KeyboardEvent) => {
    if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
    e.preventDefault();
    const all = Array.from(ref.current!.querySelectorAll<HTMLButtonElement>(":scope > button:not(:disabled)"));
    const i = all.indexOf(document.activeElement as HTMLButtonElement);
    all[(i + (e.key === "ArrowDown" ? 1 : -1) + all.length) % all.length]?.focus();
  };

  return (
    <div ref={ref} className="cmenu" role="menu" style={pos} onKeyDown={move} onContextMenu={e => e.preventDefault()}>
      {items.map((it, i) => "sep" in it ? <div key={i} className="cmenu-sep" role="separator" /> : (
        <button key={i} type="button" role="menuitem" className={`cmenu-it${it.danger ? " danger" : ""}${sub?.i === i ? " open" : ""}`} disabled={it.disabled}
          aria-haspopup={it.sub ? "menu" : undefined}
          onMouseEnter={e => hover(e.currentTarget, i, !!it.sub)} onFocus={e => hover(e.currentTarget, i, !!it.sub)}
          onClick={() => { if (it.sub) return; onClose(); it.onClick?.(); }}>
          <span className="cmenu-ic" aria-hidden="true">{it.icon ?? ""}</span>
          <span className="cmenu-lb">{it.label}</span>
          {it.hint && <span className="cmenu-hint">{it.hint}</span>}
          {it.sub && <span className="cmenu-ar" aria-hidden="true">›</span>}
        </button>
      ))}
      {sub && "sub" in items[sub.i] && <Panel x={sub.x} y={sub.y} flipFrom={sub.left} items={(items[sub.i] as { sub: MenuItem[] }).sub} onClose={onClose} />}
    </div>
  );
}
