import { useEffect, useState } from "react";
import { dialog } from "./Dialog";
import { claudeInstallNpm, getCliUpdates, getConfig, machineCheck, niceError, saveConfig, updateCli, type CliInfo, type Config, type Engine, type MachineCheck } from "./api";
import { AGENT_ICON, agentStatus, needOf, startStep, useAgents } from "./AgentSetup";

/** Mục "Trợ lý AI" của trang Cài đặt: danh sách agent (trạng thái, cài/đăng nhập/cập nhật), agent mặc định cho phiên mới, API key. */
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

        <AgentList keySet={!!cfg?.keySet} engine={engine} setEngine={setEngine} onChanged={() => void load()} focusKey={() => document.getElementById("key")?.focus()} />
        <MachineCheckCard />
        {engine === "codex" && <p className="help">Codex chạy ở chế độ chỉ đọc, không có người duyệt, chỉ dùng các tool MCP của bạn (đã tắt điều khiển máy và trình duyệt). Danh sách model lấy từ chính Codex; mỗi cuộc trò chuyện chọn model riêng ở thanh dưới ô nhập.</p>}

        <label htmlFor="key">Anthropic API key (cho agent Claude API)</label>
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

/**
 * Danh sách agent: mỗi dòng có trạng thái (phiên bản, đã cài / đăng nhập / có key) và nút Cài / Đăng nhập / Cập nhật / Nhập key.
 * Chọn một dòng làm "Agent mặc định cho phiên mới" (lưu khi bấm Lưu); mỗi phiên vẫn chọn agent riêng khi tạo.
 */
function AgentList({ keySet, engine, setEngine, onChanged, focusKey }: { keySet: boolean; engine: Engine; setEngine: (e: Engine) => void; onChanged: () => void; focusKey: () => void }) {
  const [waiting, setWaiting] = useState<Engine | null>(null);
  const [err, setErr] = useState("");
  const [clis, setClis] = useState<CliInfo[]>([]);
  const { list, err: loadErr, refresh } = useAgents(!!waiting || clis.some(c => c.updating));
  useEffect(() => { void refresh(); }, [keySet]);   // vừa lưu/xóa key
  const loadClis = () => getCliUpdates().then(setClis).catch(() => {});
  useEffect(() => { void loadClis(); }, []);
  useEffect(() => { if (clis.some(c => c.updating)) { const t = setInterval(() => { void loadClis(); }, 3000); return () => clearInterval(t); } }, [clis.some(c => c.updating)]);
  const sig = list.map(a => `${a.id}${a.installed}${a.loggedIn}`).join();
  useEffect(() => { if (list.length) onChanged(); if (waiting && list.find(a => a.id === waiting)?.loggedIn) setWaiting(null); }, [sig]);

  const act = async (fn: () => Promise<unknown>, wait?: Engine) => {
    setErr("");
    try { await fn(); if (wait) setWaiting(wait); await refresh(); await loadClis(); } catch (e) { setErr(niceError(e)); }
  };
  const CLI_ID: Record<string, string> = { cli: "claude", codex: "codex" };

  return (
    <fieldset className="engine agents">
      <legend>Agent</legend>
      <p className="help agents-note">Chọn <b>Agent mặc định cho phiên mới</b>. Mỗi phiên vẫn đổi được agent khi tạo (nút + cạnh tên dự án).</p>
      {!list.length && !loadErr && <p className="help">Đang kiểm tra các agent trên máy này…</p>}
      {list.map(a => {
        const need = needOf(a);
        const up = clis.find(c => c.id === CLI_ID[a.id]);
        return (
          <div key={a.id} className={`agent-row${engine === a.id ? " on" : ""}`}>
            <label className="agent-pick">
              <input type="radio" name="engine" checked={engine === a.id} onChange={() => setEngine(a.id)} aria-describedby={`ag-st-${a.id}`} />
              <span className={`agent-ic a-${a.id}`} aria-hidden="true">{AGENT_ICON[a.id]}</span>
              <span className="agent-main">
                <b>{a.id === "cli" ? "Claude CLI" : a.id === "codex" ? "Codex CLI" : "Claude API"}</b>
                <small>{a.id === "cli" ? "Tài khoản Claude Pro/Max đã đăng nhập" : a.id === "codex" ? "Tài khoản ChatGPT/OpenAI, model của OpenAI" : "Anthropic API key, tính tiền theo lượng dùng"}</small>
                <small id={`ag-st-${a.id}`} className={`agent-st${need ? " warn" : " ok"}`}>
                  {(a.installing || waiting === a.id || up?.updating) && <span className="spin" aria-hidden="true" />}
                  {up?.updating ? `Đang cập nhật… ${up.progress ?? ""}` : agentStatus(a, waiting === a.id)}
                  {up?.updateAvailable && !up.updating ? ` · có bản mới ${up.latest}` : ""}
                </small>
              </span>
            </label>
            {engine === a.id && <span className="agent-def">Mặc định</span>}
            <span className="agent-acts">
              {need === "install" && <button type="button" className="primary" disabled={a.installing} onClick={() => act(() => startStep(a.id, "install"))}>{a.installing ? "Đang cài…" : "Cài"}</button>}
              {need === "login" && <button type="button" className="primary" disabled={waiting === a.id} onClick={() => act(() => startStep(a.id, "login"), a.id)}>{waiting === a.id ? "Đang chờ…" : "Đăng nhập"}</button>}
              {need === "key" && <button type="button" className="primary" onClick={focusKey}>Nhập key</button>}
              {need === "git" && <button type="button" className="primary" onClick={() => act(() => startStep(a.id, "git"), a.id)}>Cài Git</button>}
              {up?.updateAvailable && up.canUpdate && !up.updating && <button type="button" onClick={() => act(() => updateCli(up.id))}>Cập nhật</button>}
            </span>
          </div>
        );
      })}
      {(err || loadErr || list.find(a => a.error)?.error) && <p className="err-msg" role="alert">{err || loadErr || list.find(a => a.error)?.error}</p>}
      {list.some(a => a.id === "cli" && a.error) && <p className="help">
        {list.find(a => a.id === "cli")?.problem === "network"
          ? <>Máy không tải được từ claude.ai. </>
          : <>Có thể cài bằng cách khác: <button type="button" className="link" onClick={() => act(claudeInstallNpm)}>Cài qua npm</button> (cần Node.js). </>}
        <a href="https://docs.anthropic.com/en/docs/claude-code/setup" target="_blank" rel="noreferrer">Mở hướng dẫn cài Claude Code</a>
      </p>}
    </fieldset>
  );
}

/** "Kiểm tra máy": các điều kiện để Claude CLI chạy được (mạng, CLI, Git Bash, PATH, npm, đăng nhập, hồ sơ), kèm nút xử lý. */
export function MachineCheckCard() {
  const [checks, setChecks] = useState<MachineCheck[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const run = async () => { setBusy(true); setErr(""); try { setChecks(await machineCheck()); } catch (e) { setErr(niceError(e)); } finally { setBusy(false); } };
  const fix = async (c: MachineCheck) => {
    try {
      if (c.fix === "install") await startStep("cli", "install");
      else if (c.fix === "login") await startStep("cli", "login");
      else if (c.fix === "git") await startStep("cli", "git");
      else window.open("https://docs.anthropic.com/en/docs/claude-code/setup", "_blank", "noreferrer");
      setTimeout(() => void run(), 4000);
    } catch (e) { setErr(niceError(e)); }
  };
  const FIX: Record<string, string> = { install: "Cài Claude CLI", login: "Đăng nhập", git: "Cài Git", guide: "Mở hướng dẫn" };
  return (
    <fieldset className="engine mcheck">
      <legend>Kiểm tra máy</legend>
      <p className="help">Các điều kiện để agent Claude chạy được trên máy này. Máy mới cài nên bấm kiểm tra một lần.</p>
      <div><button type="button" onClick={() => void run()} disabled={busy}>{busy ? "Đang kiểm tra…" : checks ? "Kiểm tra lại" : "Kiểm tra máy"}</button></div>
      {checks && <ul className="mcheck-list">
        {checks.map(c => <li key={c.id} className={c.ok ? "ok" : "bad"}>
          <span className="mcheck-dot" aria-hidden="true">{c.ok ? "✓" : "✗"}</span>
          <span className="mcheck-main"><b>{c.label}</b><small>{c.detail}</small></span>
          {c.fix && <button type="button" className={c.ok ? "" : "primary"} onClick={() => void fix(c)}>{FIX[c.fix]}</button>}
        </li>)}
      </ul>}
      {err && <p className="err-msg" role="alert">{err}</p>}
    </fieldset>
  );
}
