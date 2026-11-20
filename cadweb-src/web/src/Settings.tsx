import { useEffect, useState } from "react";
import { dialog } from "./Dialog";
import { claudeInstall, claudeLogin, claudeStatus, getConfig, niceError, saveConfig, type ClaudeStatus, type Config } from "./api";

/** Mục "Trợ lý AI" của trang Cài đặt: cách gọi trợ lý (Claude CLI / API key / Codex) và API key. */
export function Settings({ onSaved, reloadKey }: { onSaved: () => void; reloadKey: string }) {
  const [cfg, setCfg] = useState<Config | null>(null);
  const [engine, setEngine] = useState<"cli" | "api" | "codex">("cli");
  const [key, setKey] = useState("");
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  const load = () => getConfig().then(c => { setCfg(c); setEngine(c.engine); setMsg(null); })
    .catch(e => {
      setMsg({ ok: false, text: niceError(e) });
    });
  useEffect(() => { void load(); }, [reloadKey]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setBusy(true); setMsg(null);
    try {
      const c = await saveConfig({ engine, ...(key.trim() ? { anthropicKey: key } : {}) });
      setCfg(c); setKey(""); setMsg({ ok: true, text: "Đã lưu." }); onSaved();
    } catch (err) { setMsg({ ok: false, text: niceError(err) }); }
    finally { setBusy(false); }
  };
  const clearKey = async () => {
    if (!(await dialog.confirm("Xóa API key đã lưu trên gateway?", { okText: "Xóa key", danger: true }))) return;
    try { setCfg(await saveConfig({ anthropicKey: "" })); setMsg({ ok: true, text: "Đã xóa key." }); }
    catch (err) { setMsg({ ok: false, text: niceError(err) }); }
  };

  return (
      <form className="sp-form" onSubmit={submit}>

        <fieldset className="engine">
          <legend>Cách gọi trợ lý</legend>
          <label className="opt"><input type="radio" name="engine" checked={engine === "cli"} onChange={() => setEngine("cli")} />
            <span><b>Claude CLI</b> (dùng tài khoản đã đăng nhập, không cần API key)
              <small>{cfg?.cliVersion ? `Đã tìm thấy: ${cfg.cliVersion}` : "Chưa có Claude CLI trên máy này."}</small></span></label>
          <ClaudeSetup onChanged={() => void load()} />
          <label className="opt"><input type="radio" name="engine" checked={engine === "api"} onChange={() => setEngine("api")} />
            <span><b>API key</b> (tính tiền theo lượng dùng)<small>Cần nhập key ở ô bên dưới.</small></span></label>
          <label className="opt"><input type="radio" name="engine" checked={engine === "codex"} onChange={() => setEngine("codex")} />
            <span><b>Codex CLI</b> (dùng tài khoản Codex đã đăng nhập, model của OpenAI)
              <small>{cfg?.codexVersion ? `Đã tìm thấy: ${cfg.codexVersion}` : "Không tìm thấy lệnh codex trên máy chạy gateway."}</small></span></label>
        </fieldset>
        {engine === "codex" && <p className="help">Codex chạy ở chế độ chỉ đọc, không có người duyệt, chỉ dùng các tool MCP của bạn (đã tắt điều khiển máy và trình duyệt). Danh sách model lấy từ chính Codex; mỗi cuộc trò chuyện chọn model riêng ở thanh dưới ô nhập.</p>}

        <label htmlFor="key">Anthropic API key{engine !== "api" ? " (chỉ cần ở chế độ API key)" : ""}</label>
        <input id="key" type="password" autoComplete="off" value={key} onChange={e => setKey(e.target.value)}
          placeholder={cfg?.keySet ? `Đang dùng ${cfg.keyHint}. Nhập key mới để thay.` : "sk-ant-..."} />
        <p className="help">
          {cfg?.keySet
            ? cfg.keySource === "env" ? "Key đang lấy từ biến môi trường của gateway. Nhập ở đây sẽ ghi đè." : "Key đã lưu trên máy chạy gateway."
            : "Chưa có key. Tạo ở console.anthropic.com. Key chỉ nằm ở gateway, trình duyệt không giữ lại."}
          {cfg?.keySource === "file" && <> <button type="button" className="link" onClick={clearKey}>Xóa key</button></>}
        </p>

        <div className="actions">
          <button className="primary" type="submit" disabled={busy}>{busy ? "Đang kiểm tra…" : "Lưu"}</button>
          {msg && <span className={msg.ok ? "ok-msg" : "err-msg"} role={msg.ok ? "status" : "alert"}>{msg.text}</span>}
        </div>
      </form>
  );
}

/** Cài Claude CLI nếu máy chưa có, rồi mở cửa sổ đăng nhập. Tự hỏi lại trạng thái trong lúc đang cài/chờ đăng nhập. */
function ClaudeSetup({ onChanged }: { onChanged: () => void }) {
  const [st, setSt] = useState<ClaudeStatus | null>(null);
  const [waitLogin, setWaitLogin] = useState(false);
  const [err, setErr] = useState("");

  const refresh = () => claudeStatus().then(s => {
    setSt(prev => { if (prev && (prev.installed !== s.installed || prev.loggedIn !== s.loggedIn)) onChanged(); return s; });
    if (s.loggedIn) setWaitLogin(false);
  }).catch(e => setErr(niceError(e)));
  useEffect(() => { void refresh(); }, []);
  useEffect(() => {
    if (!st?.installing && !waitLogin) return;
    const t = setInterval(() => { void refresh(); }, 3000);
    return () => clearInterval(t);
  }, [st?.installing, waitLogin]);

  if (!st) return null;
  const act = async (fn: () => Promise<unknown>, after?: () => void) => {
    setErr("");
    try { await fn(); after?.(); await refresh(); } catch (e) { setErr(niceError(e)); }
  };

  return (
    <div className="claude-setup">
      {st.installing ? <p className="help">Đang tải và cài Claude CLI… (thường 1–2 phút)</p>
        : !st.installed ? <>
            <button type="button" onClick={() => act(claudeInstall)}>Tải và cài Claude CLI</button>
            <p className="help">Tải bộ cài chính thức của Anthropic, không cần quyền quản trị. Cài xong chỉ cần đăng nhập.</p>
          </>
        : st.loggedIn ? <p className="help">Đã đăng nhập{st.email ? `: ${st.email}` : ""}.</p>
        : <>
            <button type="button" className="primary" onClick={() => act(claudeLogin, () => setWaitLogin(true))}>Đăng nhập Claude</button>
            <p className="help">{waitLogin
              ? "Đã mở cửa sổ đăng nhập trên máy này. Làm theo trang Claude vừa mở trong trình duyệt; xong trang này tự cập nhật."
              : "Claude CLI đã cài nhưng chưa đăng nhập. Bấm nút để mở cửa sổ đăng nhập (dùng tài khoản Claude Pro/Max hoặc Console)."}</p>
          </>}
      {(err || st.installError) && <p className="err-msg" role="alert">{err || st.installError}</p>}
    </div>
  );
}
