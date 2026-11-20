import { useEffect, useRef, useState } from "react";

type Req =
  | { kind: "confirm"; title: string; body?: string; okText: string; danger?: boolean; done: (v: boolean) => void }
  | { kind: "prompt"; title: string; value: string; okText: string; done: (v: string | null) => void };

let open: ((r: Req) => void) | null = null;

/** Thay confirm()/prompt() của trình duyệt: gọi được từ mọi nơi, trả về Promise. */
export const dialog = {
  confirm: (title: string, o: { body?: string; okText?: string; danger?: boolean } = {}) =>
    new Promise<boolean>(res => (open ? open({ kind: "confirm", title, body: o.body, okText: o.okText ?? "Đồng ý", danger: o.danger, done: res }) : res(false))),
  prompt: (title: string, value = "", okText = "Lưu") =>
    new Promise<string | null>(res => (open ? open({ kind: "prompt", title, value, okText, done: res }) : res(null))),
};

/** Đặt một lần ở gốc ứng dụng. Dùng thẻ <dialog> gốc: nằm giữa màn hình, khóa focus, Esc để hủy. */
export function DialogHost() {
  const [req, setReq] = useState<Req | null>(null);
  const [text, setText] = useState("");
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => { open = r => { setText(r.kind === "prompt" ? r.value : ""); setReq(r); }; return () => { open = null; }; }, []);
  useEffect(() => { if (req) ref.current?.showModal(); }, [req]);

  const close = (ok: boolean) => {
    if (!req) return;
    const r = req; setReq(null); ref.current?.close();
    if (r.kind === "confirm") r.done(ok); else r.done(ok ? text : null);
  };

  if (!req) return null;
  return (
    <dialog ref={ref} className="dlg" onCancel={e => { e.preventDefault(); close(false); }}
      onClick={e => { if (e.target === ref.current) close(false); }} aria-labelledby="dlg-t">
      <form method="dialog" onSubmit={e => { e.preventDefault(); close(true); }}>
        <h2 id="dlg-t">{req.title}</h2>
        {req.kind === "confirm" && req.body && (/^\s*[{\[]/.test(req.body) ? <pre className="dlg-body">{req.body}</pre> : <p className="dlg-text">{req.body}</p>)}
        {req.kind === "prompt" && <input autoFocus value={text} onChange={e => setText(e.target.value)} onFocus={e => e.currentTarget.select()} aria-label={req.title} />}
        <div className="dlg-actions">
          <button type="button" onClick={() => close(false)}>Hủy</button>
          <button type="submit" className={req.kind === "confirm" && req.danger ? "danger" : "primary"} autoFocus={req.kind === "confirm"}>{req.okText}</button>
        </div>
      </form>
    </dialog>
  );
}
