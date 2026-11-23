import { useEffect, useRef, useState } from "react";
import { coordPost, coordRevoke, EMPTY_COORD, getCoord, niceError, type Coord, type CoordLock } from "./api";
import { LockIcon } from "./ProjectTree";

/** Đọc bảng điều phối của dự án bằng poll (3 giây; tab ẩn thì 15 giây). */
export function useCoord(project: string, tick: number) {
  const [c, setC] = useState<Coord>(EMPTY_COORD);
  const [n, setN] = useState(0);
  useEffect(() => {
    if (!project) return;
    let alive = true, t: ReturnType<typeof setTimeout>;
    const load = () => getCoord(project).then(x => { if (alive) setC(x); }).catch(() => {}).finally(() => {
      if (alive) t = setTimeout(load, document.hidden ? 15000 : 3000);
    });
    void load();
    return () => { alive = false; clearTimeout(t); };
  }, [project, tick, n]);
  useEffect(() => { setC(EMPTY_COORD); }, [project]);
  return { coord: c, reload: () => setN(x => x + 1) };
}

export const locksByOwner = (c: Coord) => c.locks.reduce<Record<string, CoordLock[]>>((m, l) => { (m[l.owner] ??= []).push(l); return m; }, {});
const hhmm = (s: string) => { const d = new Date(s); return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`; };
const RECENT_MS = 2 * 3600_000;   // dải "Đang làm" chỉ hiện phiên đang chạy hoặc vừa hoạt động trong 2 giờ
const EngTag = ({ e }: { e: string }) => <span className={`eng eng-${e === "codex" ? "codex" : "claude"}`}>{e === "codex" ? "Codex" : "Claude"}</span>;

/** Dải "Đang làm": mỗi phiên một chip (tên · engine · việc · chấm trạng thái). */
export function CoordStrip({ coord }: { coord: Coord }) {
  const now = Date.parse(coord.now) || Date.now();
  const list = Object.entries(coord.agents).filter(([id, a]) => coord.running.includes(id) || now - Date.parse(a.heartbeat) < RECENT_MS)
    .sort(([a], [b]) => Number(coord.running.includes(b)) - Number(coord.running.includes(a)));
  if (!list.length) return null;
  const locks = locksByOwner(coord);
  return (
    <div className="cstrip" aria-label="Các phiên đang làm">
      <span className="cstrip-lbl">Đang làm</span>
      {list.map(([id, a]) => {
        const run = coord.running.includes(id);
        return (
          <span key={id} className={`cchip${run ? " on" : ""}`} title={`${a.label}\n${run ? "Đang chạy lượt" : "Rảnh"}${locks[id] ? `\nKhoá: ${locks[id].map(l => l.target).join(", ")}` : ""}`}>
            <span className={`cdot${run ? "" : " idle"}`} aria-label={run ? "đang chạy" : "rảnh"} />
            <b>{a.label}</b><EngTag e={a.engine} />
            {a.task && <span className="cchip-task">{a.task}</span>}
            {locks[id] && <span className="clock"><LockIcon />{locks[id].length}</span>}
          </span>
        );
      })}
    </div>
  );
}

const KIND: Record<string, string> = { handoff: "bàn giao", question: "hỏi", note: "ghi chú", lock: "khoá", system: "hệ thống" };

/** Tab Trao đổi: dòng thời gian coord-log.jsonl, người dùng gửi tin cho mọi agent. */
function Timeline({ project, coord, reload }: { project: string; coord: Coord; reload: () => void }) {
  const [text, setText] = useState(""); const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  const name = (id: string) => id === "user" ? "Bạn" : id === "system" ? "Hệ thống" : coord.agents[id]?.label ?? id;
  const send = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;
    setBusy(true); setErr("");
    try { await coordPost(project, text.trim()); setText(""); reload(); } catch (x) { setErr(niceError(x)); } finally { setBusy(false); }
  };
  const top = useRef<HTMLDivElement>(null);
  return (
    <div className="cpane">
      <form className="cpost" onSubmit={send}>
        <input value={text} onChange={e => setText(e.target.value)} placeholder="Nhắn cho mọi agent (to: *)" maxLength={1000} aria-label="Tin nhắn cho mọi agent" />
        <button type="submit" disabled={busy || !text.trim()}>Gửi</button>
      </form>
      {err && <p className="err-msg small" role="alert">{err}</p>}
      <div className="clog" ref={top}>
        {coord.log.length ? [...coord.log].reverse().map((m, i) => (
          <div key={`${m.t}-${i}`} className="cev">
            <time dateTime={m.t}>{hhmm(m.t)}</time>
            <div>
              <span className="cev-who">{name(m.from)}</span>
              <span className={`ckind ck-${m.kind}`}>{KIND[m.kind] ?? m.kind}</span>
              {m.to !== "*" && <small className="cev-to">→ {name(m.to)}</small>}
              <p>{m.text}</p>
            </div>
          </div>
        )) : <p className="cempty">Chưa có trao đổi nào. Bàn giao, câu hỏi giữa các agent sẽ hiện ở đây; bạn cũng gửi tin cho tất cả được.</p>}
      </div>
    </div>
  );
}

/** Tab Khoá: danh sách khoá đang giữ, nút Thu hồi (ép thả khi agent kẹt). */
function Locks({ project, coord, reload }: { project: string; coord: Coord; reload: () => void }) {
  const [err, setErr] = useState("");
  const revoke = async (l: CoordLock) => {
    setErr("");
    try { await coordRevoke(project, l.id); reload(); } catch (x) { setErr(niceError(x)); }
  };
  return (
    <div className="cpane">
      {err && <p className="err-msg small" role="alert">{err}</p>}
      {coord.locks.length ? coord.locks.map(l => (
        <div key={l.id} className="clockrow">
          <div>
            <code title={l.target}>{l.target}</code>
            <small>{coord.agents[l.owner]?.label ?? l.owner} · {l.mode === "write" ? "ghi" : "đọc"}{l.reason ? ` · ${l.reason}` : ""} · tới {hhmm(l.expires)}</small>
          </div>
          <button type="button" onClick={() => void revoke(l)} title="Ép thả khoá này (khi agent bị kẹt)">Thu hồi</button>
        </div>
      )) : <p className="cempty">Không có khoá nào đang giữ.</p>}
    </div>
  );
}

/** Nội dung tab Trao đổi / Khoá ở cột phải. */
export function CoordPanel({ tab, project, coord, reload }: { tab: "log" | "locks"; project: string; coord: Coord; reload: () => void }) {
  return tab === "log" ? <Timeline project={project} coord={coord} reload={reload} /> : <Locks project={project} coord={coord} reload={reload} />;
}
