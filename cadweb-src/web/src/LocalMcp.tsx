import { useCallback, useEffect, useState } from "react";
import { health, niceError, type Health } from "./api";

/**
 * Tab MCP của bản local: không có máy CAD "từ xa" để nối — gateway gọi thẳng MCP của chính máy này
 * (phục vụ bởi AutoCAD MCP Launcher ở 127.0.0.1:8764), nên tab này chỉ hiện trạng thái, không có bước nối máy.
 */
export function LocalMcp({ onChanged }: { onChanged: () => void }) {
  const [h, setH] = useState<Health | null | undefined>(undefined);   // undefined = đang tải
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    setBusy(true);
    return health().then(r => { setH(r); setErr(""); }).catch(e => { setH(null); setErr(niceError(e)); }).finally(() => setBusy(false));
  }, []);
  useEffect(() => { void load(); }, [load]);

  const refresh = () => { void load().then(onChanged); };

  return (
    <section className="mcp-in">
        <div className="mcp-head">
          <div className="mcp-btns"><button className="primary" disabled={busy} onClick={refresh}>{busy ? "Đang kiểm tra…" : "Kiểm tra lại"}</button></div>
        </div>
        <p className="desc">
          Bản local gọi thẳng MCP của <b>chính máy này</b>, phục vụ bởi <b>AutoCAD MCP Launcher</b> ở <code>127.0.0.1:8764</code>.
          Không cần nối máy hay token: mở launcher, bấm <b>Bật kết nối cho agent</b>, rồi bấm "Kiểm tra lại" ở đây.
          Muốn đổi danh sách MCP (thêm litebim/litecad, hay bớt MCP không dùng) thì sửa biến <code>LOCAL_MCP</code> trong <code>gateway/.env</code> rồi khởi động lại gateway.
        </p>
        {err && <p className="banner" role="alert">{err}</p>}

        {h === undefined ? <p className="desc">Đang tải…</p> : h === null ? null : (
          <ul className="srv mym-list">
            {h.servers.map(s => (
              <li key={s.id} className={s.ok ? "" : "off"}>
                <div className="srv-top">
                  <span className="srv-name">{s.name}</span>
                  <span className="badge">{s.id}</span>
                  <span className={`badge ${s.ok ? "" : "mym-bad"}`}>{s.ok ? `${s.tools} tool` : "lỗi"}</span>
                </div>
                <p className="srv-sub">{s.ok ? `http://127.0.0.1:8764/${s.id}/mcp` : s.error}</p>
              </li>
            ))}
          </ul>
        )}
    </section>
  );
}
