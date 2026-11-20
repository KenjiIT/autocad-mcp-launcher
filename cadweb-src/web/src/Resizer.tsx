import { useEffect } from "react";

// Thanh kéo đổi bề rộng cột (như Orca): kéo cạnh cột để rộng/hẹp, bấm đúp để về mặc định.
// Bề rộng lưu trong biến CSS trên <html> và localStorage nên giữ nguyên khi tải lại trang.
type Props = { name: "side" | "files"; def: number; min: number; max: number; edge: "right" | "left" };
const key = (n: string) => `cad-w-${n}`;
const apply = (n: string, w: number) => document.documentElement.style.setProperty(`--${n}-w`, `${w}px`);

export function Resizer({ name, def, min, max, edge }: Props) {
  useEffect(() => {
    let w = def; try { const v = Number(localStorage.getItem(key(name))); if (v) w = Math.min(max, Math.max(min, v)); } catch { /* bỏ qua */ }
    apply(name, w);
  }, [name, def, min, max]);

  const down = (e: React.PointerEvent<HTMLDivElement>) => {
    if (e.button !== 0) return;
    e.preventDefault();
    const col = e.currentTarget.parentElement!; const start = e.clientX; const w0 = col.getBoundingClientRect().width;
    document.body.classList.add("resizing");
    const move = (ev: PointerEvent) => {
      const d = ev.clientX - start; const w = Math.round(Math.min(max, Math.max(min, edge === "right" ? w0 + d : w0 - d)));
      apply(name, w); try { localStorage.setItem(key(name), String(w)); } catch { /* bỏ qua */ }
    };
    const up = () => { document.body.classList.remove("resizing"); window.removeEventListener("pointermove", move); window.removeEventListener("pointerup", up); };
    window.addEventListener("pointermove", move); window.addEventListener("pointerup", up);
  };
  const reset = () => { apply(name, def); try { localStorage.removeItem(key(name)); } catch { /* bỏ qua */ } };

  return <div className={`resizer ${edge}`} role="separator" aria-orientation="vertical" aria-label="Kéo để đổi bề rộng cột"
    title="Kéo để đổi bề rộng · bấm đúp để về mặc định" onPointerDown={down} onDoubleClick={reset} />;
}
