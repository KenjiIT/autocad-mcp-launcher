import { useEffect, useRef, useState } from "react";
import { claudeGit, claudeInstall, claudeLogin, codexInstall, codexLogin, listAgents, niceError, saveConfig, type Agent, type Engine } from "./api";

/** Agent còn thiếu bước nào trước khi dùng được: cài, đăng nhập, hay nhập API key. null = sẵn sàng. */
export type Need = "install" | "login" | "key" | "git" | null;
export const needOf = (a: Agent): Need => a.id === "api" ? (a.loggedIn ? null : "key") : !a.installed ? "install" : !a.loggedIn ? "login" : null;   // thiếu Git Bash không chặn (Claude Code dùng PowerShell)
export const NEED_LABEL: Record<Exclude<Need, null>, string> = { install: "Cài đặt", login: "Đăng nhập", key: "Nhập key", git: "Cài Git" };
export const AGENT_ICON: Record<string, string> = { cli: "✳", codex: "◎", api: "⚿" };

/** Dòng trạng thái ngắn của một agent (phiên bản, đã cài/đăng nhập/có key, đang cài…). */
export function agentStatus(a: Agent, waiting = false): string {
  if (a.installing) return "Đang cài… (thường 1–2 phút)";
  if (waiting && a.installed && !a.loggedIn && a.id !== "api") return "Đang chờ đăng nhập trong cửa sổ vừa mở…";
  if (a.id === "api") return a.loggedIn ? "Đã có API key" : "Chưa có API key";
  if (!a.installed) return "Chưa cài trên máy này";
  return `${a.version ?? "Đã cài"} · ${a.loggedIn ? `đã đăng nhập${a.account ? ` (${a.account})` : ""}` : "chưa đăng nhập"}`;
}

/** Bắt đầu cài / mở cửa sổ đăng nhập. Nhập key làm riêng (cần ô nhập). */
export const startStep = (id: Engine, need: "install" | "login" | "git") =>
  need === "git" ? claudeGit() : need === "install" ? (id === "codex" ? codexInstall() : claudeInstall()) : (id === "codex" ? codexLogin() : claudeLogin());

/** Hỏi lại danh sách agent mỗi 3 giây khi `active` (đang cài / chờ đăng nhập). */
export function useAgents(active: boolean) {
  const [list, setList] = useState<Agent[]>([]);
  const [def, setDef] = useState<Engine>("cli");
  const [err, setErr] = useState("");
  const refresh = () => listAgents().then(r => { setList(r.agents); setDef(r.default); setErr(""); return r.agents; })
    .catch(e => { setErr(niceError(e)); return [] as Agent[]; });
  useEffect(() => { void refresh(); }, []);
  const busy = active || list.some(a => a.installing);
  useEffect(() => {
    if (!busy) return;
    const t = setInterval(() => { void refresh(); }, 3000);
    return () => clearInterval(t);
  }, [busy]);
  return { list, def, setDef, err, refresh };
}

/**
 * Cửa sổ "chuẩn bị agent" mở từ menu tạo phiên: làm tại chỗ bước còn thiếu (cài → đăng nhập, hoặc nhập key),
 * tự theo dõi tới khi agent sẵn sàng rồi gọi onReady (tạo phiên luôn).
 */
export function AgentGate({ agent, onReady, onCancel }: { agent: Agent; onReady: () => void; onCancel: () => void }) {
  const ref = useRef<HTMLDialogElement>(null);
  const [waiting, setWaiting] = useState(false);
  const [key, setKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const loginStarted = useRef(false);
  const { list, refresh } = useAgents(waiting);
  const a = list.find(x => x.id === agent.id) ?? agent;
  const need = needOf(a);
  useEffect(() => { ref.current?.showModal(); }, []);
  useEffect(() => { if (list.length && need === null) onReady(); }, [need, list.length]);
  useEffect(() => { if (a.error) { setErr(a.error); setWaiting(false); } }, [a.error]);
  // Cài xong mà chưa đăng nhập: thôi chờ để hiện nút Đăng nhập.
  useEffect(() => { if (waiting && need === "login" && !a.installing && a.installed && !loginStarted.current) setWaiting(false); }, [need, a.installing]);

  const go = async () => {
    if (!need) return;
    setErr(""); setBusy(true);
    try {
      if (need === "key") { await saveConfig({ anthropicKey: key.trim() }); await refresh(); }
      else { loginStarted.current = need === "login"; await startStep(a.id, need); setWaiting(true); await refresh(); }
    } catch (e) { setErr(niceError(e)); } finally { setBusy(false); }
  };
  const text = need === "git" ? "Claude Code trên Windows cần Git for Windows (có Git Bash) để chạy lệnh. Bấm Cài Git: máy có winget thì cài thẳng trong cửa sổ mới, không thì mở trang tải; cài xong quay lại đây."
    : need === "install" ? `${a.name} chưa được cài trên máy này. Bấm Cài đặt để tải và cài (không cần quyền quản trị); xong sẽ chuyển sang đăng nhập.`
    : need === "login" ? `${a.name} đã cài nhưng chưa đăng nhập. Bấm Đăng nhập để mở cửa sổ đăng nhập trên máy này, làm theo trang vừa mở trong trình duyệt.`
    : "Nhập Anthropic API key (tạo ở console.anthropic.com). Key chỉ lưu ở gateway trên máy này.";

  return (
    <dialog ref={ref} className="dlg agate" aria-labelledby="agate-t"
      onCancel={e => { e.preventDefault(); onCancel(); }} onClick={e => { if (e.target === ref.current) onCancel(); }}>
      <form onSubmit={e => { e.preventDefault(); void go(); }}>
        <h2 id="agate-t"><span className={`agent-ic a-${a.id}`} aria-hidden="true">{AGENT_ICON[a.id]}</span>Phiên mới với {a.name}</h2>
        <p className="dlg-text">{text}</p>
        <p className="agate-st" role="status">{a.installing || waiting ? <span className="spin" aria-hidden="true" /> : null}{agentStatus(a, waiting)}</p>
        {need === "key" && <input type="password" autoFocus autoComplete="off" value={key} onChange={e => setKey(e.target.value)} placeholder="sk-ant-..." aria-label="Anthropic API key" />}
        {err && <p className="err-msg" role="alert">{err}</p>}
        <div className="dlg-actions">
          <button type="button" onClick={onCancel}>Hủy</button>
          {need && <button type="submit" className="primary" disabled={busy || a.installing || (need === "key" && !key.trim()) || (waiting && need === "login")}>
            {busy ? "Đang làm…" : waiting && need === "login" ? "Đang chờ đăng nhập…" : NEED_LABEL[need]}</button>}
        </div>
        <p className="help agate-note">Xong bước này phiên chat được tạo luôn.</p>
      </form>
    </dialog>
  );
}
