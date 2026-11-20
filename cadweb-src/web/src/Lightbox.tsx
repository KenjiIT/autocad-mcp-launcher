import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

// Xem ảnh ngay trong trang (cửa sổ nổi), không mở tab mới.
// Lăn chuột để phóng to/thu nhỏ quanh con trỏ, kéo để di chuyển, bấm đúp để về vừa khung, Esc hoặc bấm nền để đóng.
export function Lightbox({ src, name, onClose }: { src: string; name?: string; onClose: () => void }) {
  const [z, setZ] = useState(1); const [p, setP] = useState({ x: 0, y: 0 });
  const drag = useRef<{ x: number; y: number; px: number; py: number } | null>(null);
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const k = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "+" || e.key === "=") zoomAt(1.25);
      if (e.key === "-") zoomAt(0.8);
      if (e.key === "0") fit();
    };
    window.addEventListener("keydown", k); return () => window.removeEventListener("keydown", k);
  });

  const fit = () => { setZ(1); setP({ x: 0, y: 0 }); };
  const zoomAt = (f: number, cx = 0, cy = 0) => {
    setZ(z0 => { const z1 = Math.min(12, Math.max(0.2, z0 * f)); const r = z1 / z0;
      setP(p0 => ({ x: cx - (cx - p0.x) * r, y: cy - (cy - p0.y) * r })); return z1; });
  };
  const wheel = (e: React.WheelEvent) => {
    const r = box.current!.getBoundingClientRect();
    zoomAt(e.deltaY < 0 ? 1.15 : 1 / 1.15, e.clientX - r.left - r.width / 2, e.clientY - r.top - r.height / 2);
  };

  return createPortal(
    <div className="lb" role="dialog" aria-modal="true" aria-label="Xem ảnh" onMouseDown={e => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="lb-win">
        <div className="lb-bar">
          <span className="lb-name">{name ?? "Ảnh"}</span>
          <span className="lb-z">{Math.round(z * 100)}%</span>
          <button type="button" className="ghost" onClick={() => zoomAt(0.8)} title="Thu nhỏ (-)">−</button>
          <button type="button" className="ghost" onClick={() => zoomAt(1.25)} title="Phóng to (+)">+</button>
          <button type="button" className="ghost" onClick={fit} title="Vừa khung (0)">Vừa khung</button>
          <a className="lb-dl" href={src} download={name ?? "anh.png"} title="Tải về">Tải về</a>
          <button type="button" className="ghost lb-x" onClick={onClose} title="Đóng (Esc)" aria-label="Đóng">
            <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 4l8 8M12 4l-8 8" /></svg></button>
        </div>
        <div className={`lb-view${drag.current ? " grab" : ""}`} ref={box} onWheel={wheel} onDoubleClick={fit}
          onPointerDown={e => { (e.target as Element).setPointerCapture?.(e.pointerId); drag.current = { x: e.clientX, y: e.clientY, px: p.x, py: p.y }; }}
          onPointerMove={e => { const d = drag.current; if (d) setP({ x: d.px + e.clientX - d.x, y: d.py + e.clientY - d.y }); }}
          onPointerUp={() => { drag.current = null; }}>
          <img src={src} alt={name ?? "Ảnh"} draggable={false} style={{ transform: `translate(${p.x}px, ${p.y}px) scale(${z})` }} />
        </div>
      </div>
    </div>, document.body);
}
