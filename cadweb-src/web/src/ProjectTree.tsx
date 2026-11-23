import { useEffect, useRef, useState } from "react";
import { AGENT_NAME, lastAgent, listAgents, locateFolder, openProject, deleteInfo, type DeleteInfo, type Agent, type Engine, createProject, deleteProject, importFiles, listConvs, listProjects, niceError, pickFiles, pickFolder, pinProject, setProjectShell, renameProject, revealFile, type ConvMeta, type CoordLock, type Project } from "./api";
import { ContextMenu, type MenuItem } from "./ContextMenu";
import { dialog } from "./Dialog";
import { AGENT_ICON, AgentGate, NEED_LABEL, needOf } from "./AgentSetup";

const ago = (t: number) => {
  const m = Math.round((Date.now() - t) / 60000);
  return m < 1 ? "vừa xong" : m < 60 ? `${m} phút` : m < 1440 ? `${Math.round(m / 60)} giờ` : `${Math.round(m / 1440)} ngày`;
};
const base = (p: string) => p.split(/[\\/]/).filter(Boolean).pop() ?? p;


type Props = {
  current: string; onSelect: (id: string) => void; onOpenOther: (project: string, conv: string) => void;
  convs: ConvMeta[]; curId: string; busy: boolean;
  running?: Set<string>;   // phiên đang có lượt chạy (chạy ngầm cũng tính)
  locks?: Record<string, CoordLock[]>;   // khoá của từng phiên chat trong dự án đang chọn
  onOpen: (id: string) => void; onRename: (c: ConvMeta) => void; onRemove: (id: string) => void;
  onNew: (project: string, engine: Engine) => void;   // tạo phiên mới trong dự án với agent đã chọn
  onProjectsChanged?: () => void;   // đổi tên/thêm file/xóa dự án: cột file bên phải tải lại
};

/**
 * Cột trái kiểu Orca: danh sách dự án, mỗi dự án mở ra là các cuộc trò chuyện của nó.
 * Dự án đang chọn dùng danh sách hội thoại của Chat (có Sửa/Xóa); dự án khác tải khi mở ra.
 */
export function ProjectTree(p: Props) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [open, setOpen] = useState<Record<string, boolean>>({});
  const [others, setOthers] = useState<Record<string, ConvMeta[]>>({});
  const [err, setErr] = useState("");
  const [adding, setAdding] = useState(false);
  const [menu, setMenu] = useState<{ x: number; y: number; items: MenuItem[] } | null>(null);
  const showMenu = (e: React.MouseEvent, items: MenuItem[]) => { e.preventDefault(); setMenu({ x: e.clientX, y: e.clientY, items }); };
  const act = (fn: () => Promise<unknown>) => () => { setErr(""); fn().catch(e => setErr(niceError(e))); };
  const copy = (text: string) => act(() => navigator.clipboard.writeText(text));

  // Agent chọn được khi tạo phiên mới: tải khi mở cột, tải lại mỗi lần mở menu (người dùng có thể vừa cài/đăng nhập).
  const [agents, setAgents] = useState<{ list: Agent[]; def: Engine }>({ list: [], def: "cli" });
  const loadAgents = () => listAgents().then(r => { const v = { list: r.agents, def: r.default }; setAgents(v); return v; });
  useEffect(() => { loadAgents().catch(() => {}); }, []);
  // Agent chưa cài / chưa đăng nhập / chưa có key không bị khoá: bấm vào mở cửa sổ làm bước còn thiếu, xong thì tạo phiên luôn.
  const [gate, setGate] = useState<{ agent: Agent; project: string } | null>(null);
  const [deleting, setDeleting] = useState<Project | null>(null);
  const afterDelete = async (pr: Project, recycled: boolean) => {
    const cur = pr.id === p.current;
    const rest = projects.filter(x => x.id !== pr.id);
    setDeleting(null);
    await load();
    if (cur && rest[0]) p.onSelect(rest[0].id);
    p.onProjectsChanged?.();
    setNote(recycled ? `Đã xóa dự án "${pr.name}" và chuyển thư mục ${pr.dir} vào Thùng rác (khôi phục được từ Thùng rác).`
      : `Đã xóa dự án "${pr.name}" khỏi CAD Studio; thư mục và file trên máy giữ nguyên.`);
  };
  const agentItems = (pr: Project, a = agents): MenuItem[] => { const def = lastAgent() ?? a.def; return a.list.length ? a.list.map(ag => {
    const need = needOf(ag);
    return {
      label: ag.name, icon: AGENT_ICON[ag.id] ?? "•",
      hint: ag.installing ? "đang cài…" : need ? `${NEED_LABEL[need]} →` : ag.id === def ? "✓ lần trước" : ag.detail,
      onClick: () => need ? setGate({ agent: ag, project: pr.id }) : p.onNew(pr.id, ag.id),
    };
  }) : [{ label: "Không tải được danh sách agent", disabled: true }]; };
  const newMenu = (e: React.MouseEvent, pr: Project) => {
    const r = e.currentTarget.getBoundingClientRect();
    const show = (a: typeof agents) => setMenu({ x: r.left, y: r.bottom + 4, items: [{ label: "Chọn agent cho phiên mới", disabled: true }, { sep: true }, ...agentItems(pr, a)] });
    show(agents);
    loadAgents().then(show).catch(() => {});
  };

  const [note, setNote] = useState("");
  const [drag, setDrag] = useState(false);
  /** Mở một thư mục làm dự án: đã là dự án thì chuyển sang dự án đó, có .cadstudio/ thì báo số phiên chat tìm thấy. */
  const openDir = async (dir: string) => {
    const r = await openProject(dir);
    await load(); p.onSelect(r.project.id); p.onProjectsChanged?.();
    setNote(r.existed ? `"${r.project.name}" đã là dự án, đã mở.` : r.sessions ? `Tìm thấy ${r.sessions} phiên chat, đã mở "${r.project.name}".` : `Đã mở "${r.project.name}".`);
  };
  const openExisting = act(async () => { setNote(""); const d = await pickFolder("open"); if (d) await openDir(d); });
  const onDrop = (e: React.DragEvent) => {
    e.preventDefault(); setDrag(false); setNote("");
    const uri = e.dataTransfer.getData("text/uri-list").split(/\r?\n/).find(u => u.startsWith("file:"));
    const entry = Array.from(e.dataTransfer.items).map(i => i.webkitGetAsEntry?.()).find(x => x);
    void act(async () => {
      if (uri) return openDir(decodeURIComponent(new URL(uri).pathname).replace(/^\/([A-Za-z]:)/, "$1"));
      if (!entry?.isDirectory) { setErr("Kéo một THƯ MỤC (không phải file) vào đây để mở làm dự án."); return; }
      // Trình duyệt chỉ cho biết tên thư mục: gateway tìm ở Desktop/Documents/Downloads/…; không chắc thì hỏi chọn thư mục.
      const dirs = await locateFolder(entry.name);
      if (dirs.length === 1) return openDir(dirs[0]);
      setNote(dirs.length ? `Có ${dirs.length} thư mục tên "${entry.name}", chọn đúng thư mục cần mở.` : `Không tự tìm được "${entry.name}", chọn thư mục cần mở.`);
      const d = await pickFolder("open"); if (d) await openDir(d);
    })();
  };
  const isFolderDrag = (e: React.DragEvent) => e.dataTransfer.types.includes("Files") || e.dataTransfer.types.includes("text/uri-list");

  const load = () => listProjects().then(l => {
    setProjects(l);
    if (!l.some(x => x.id === p.current) && l[0]) p.onSelect(l[0].id);
  }).catch(e => setErr(niceError(e)));
  useEffect(() => { void load(); }, []);

  const isOpen = (id: string) => open[id] ?? id === p.current;
  const toggle = (id: string) => {
    const next = !isOpen(id);
    setOpen(o => ({ ...o, [id]: next }));
    if (next && id !== p.current) listConvs(id).then(c => setOthers(o => ({ ...o, [id]: c }))).catch(e => setErr(niceError(e)));
  };

  const projectMenu = (pr: Project): MenuItem[] => {
    const cur = pr.id === p.current;
    return [
      { label: "Phiên chat mới", icon: "+", sub: agentItems(pr) },
      { label: "Thêm file vào dự án…", icon: "↥", disabled: !pr.dir, onClick: act(async () => {
        const f = await pickFiles(); if (f.length) { await importFiles(pr.id, f); p.onProjectsChanged?.(); }
      }) },
      { sep: true },
      { label: "Đổi tên…", icon: "✎", onClick: act(async () => {
        const n = (await dialog.prompt("Đổi tên dự án", pr.name))?.trim();
        if (n && n !== pr.name) { await renameProject(pr.id, n); await load(); p.onProjectsChanged?.(); }
      }) },
      ...(pr.dir ? [{ label: pr.shell ? "Tắt cho agent chạy lệnh" : "Cho agent chạy lệnh…", icon: pr.shell ? "■" : "▶", onClick: act(async () => {
        if (!pr.shell && !(await dialog.confirm("Cho agent chạy lệnh trong dự án này?", { body: `Agent sẽ được chạy lệnh (Python, script, Excel…) trên máy này, trong thư mục ${pr.dir}. Chỉ bật khi cần, và tắt khi xong.`, okText: "Cho phép" }))) return;
        await setProjectShell(pr.id, !pr.shell); await load();
      }) }] : []),
      { label: pr.pinned ? "Bỏ ghim" : "Ghim lên đầu", icon: pr.pinned ? "○" : "◉", onClick: act(async () => { await pinProject(pr.id, !pr.pinned); await load(); }) },
      { sep: true },
      { label: "Mở thư mục trong Explorer", icon: "↗", disabled: !pr.dir, onClick: act(() => revealFile(pr.id)) },
      { label: "Sao chép", icon: "⧉", sub: [
        { label: "Đường dẫn thư mục", disabled: !pr.dir, onClick: copy(pr.dir ?? "") },
        { label: "Tên dự án", onClick: copy(pr.name) },
      ] },
      { sep: true },
      { label: "Xóa dự án khỏi CAD Studio", icon: "✕", danger: true, disabled: projects.length < 2, onClick: () => { setErr(""); setNote(""); setDeleting(pr); } },
    ];
  };
  const convMenu = (pr: Project, c: ConvMeta): MenuItem[] => {
    const cur = pr.id === p.current;
    return [
      { label: "Mở", icon: "↗", onClick: () => cur ? p.onOpen(c.id) : p.onOpenOther(pr.id, c.id) },
      { label: "Đổi tên…", icon: "✎", disabled: !cur, onClick: () => p.onRename(c) },
      { label: "Sao chép tiêu đề", icon: "⧉", onClick: copy(c.title) },
      { sep: true },
      { label: "Xóa phiên chat", icon: "✕", danger: true, disabled: !cur || !!p.running?.has(c.id), onClick: () => p.onRemove(c.id) },
    ];
  };

  return (
    <div className={`ptree${drag ? " drop" : ""}`}
      onDragOver={e => { if (isFolderDrag(e)) { e.preventDefault(); e.dataTransfer.dropEffect = "copy"; setDrag(true); } }}
      onDragLeave={e => { if (!e.currentTarget.contains(e.relatedTarget as Node)) setDrag(false); }}
      onDrop={e => { if (isFolderDrag(e)) onDrop(e); }}>
      {menu && <ContextMenu x={menu.x} y={menu.y} items={menu.items} onClose={() => setMenu(null)} />}
      {deleting && <DeleteProject project={deleting} onCancel={() => setDeleting(null)} onDone={r => void afterDelete(deleting, r)} />}
      {gate && <AgentGate agent={gate.agent} onCancel={() => setGate(null)} onReady={() => { const g = gate; setGate(null); void loadAgents().catch(() => {}); p.onNew(g.project, g.agent.id); }} />}
      <div className="ptree-head"><span>Dự án</span></div>
      {projects.length > 0 && <div className="ptree-acts">
        <button type="button" className="pnew" onClick={() => { setErr(""); setNote(""); setAdding(true); }}><span aria-hidden="true">+</span>Dự án mới</button>
        <button type="button" className="popen" onClick={openExisting} title="Chọn một thư mục trên máy để mở làm dự án">Mở dự án có sẵn…</button>
      </div>}
      {adding && <NewProject onCancel={() => setAdding(false)} onCreated={async id => { setAdding(false); await load(); p.onSelect(id); }} />}
      {err && <p className="err-msg small" role="alert">{err}</p>}
      {note && <p className="ok-msg small ptree-note" role="status">{note}</p>}
      {drag && <div className="ptree-drop" aria-hidden="true"><svg viewBox="0 0 16 16"><path d="M1.5 3.5h4l1.5 1.5h7.5v8h-13z" /></svg>Thả thư mục để mở làm dự án</div>}
      {!projects.length && !err && <div className="ptree-empty">
        <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M1.5 3.5h4l1.5 1.5h7.5v8h-13z" /></svg>
        <b>Chưa có dự án</b>
        <p>Mỗi dự án là một thư mục trên máy: hồ sơ, bản vẽ và các phiên chat của agent nằm chung trong đó.</p>
        <button type="button" className="pnew" onClick={() => { setErr(""); setAdding(true); }}><span aria-hidden="true">+</span>Dự án mới</button>
        <button type="button" className="popen" onClick={openExisting}>Mở dự án có sẵn…</button>
        <small>hoặc kéo thả một thư mục vào đây</small>
      </div>}
      <div className="ptree-list">
        {projects.map(pr => {
          const cur = pr.id === p.current, list = cur ? p.convs : others[pr.id] ?? [];
          return (
            <div key={pr.id} className={`pnode${cur ? " cur" : ""}`}>
              <div className="prow" onContextMenu={e => showMenu(e, projectMenu(pr))}>
                <button type="button" className="prow-tw" aria-label={isOpen(pr.id) ? "Thu gọn" : "Mở ra"} onClick={() => toggle(pr.id)}>{isOpen(pr.id) ? "▾" : "▸"}</button>
                <button type="button" className="prow-name" title={pr.dir ?? "Không gắn thư mục"} onClick={() => cur ? toggle(pr.id) : p.running?.size ? setErr("Đợi phiên đang chạy xong rồi mới chuyển sang dự án khác (chuyển dự án sẽ ngắt phiên đang chạy).") : p.onSelect(pr.id)}>
                  <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M1.5 3.5h4l1.5 1.5h7.5v8h-13z" /></svg>{pr.name}{pr.pinned && <span className="ppin" title="Đã ghim">●</span>}{pr.shell && <span className="pshell" title="Agent được chạy lệnh trong dự án này">&gt;_</span>}
                </button>
                <button type="button" className="prow-add" title="Phiên chat mới (chọn agent)" aria-label={`Phiên chat mới trong ${pr.name}`} aria-haspopup="menu"
                  onClick={e => newMenu(e, pr)}>+</button>
              </div>
              {isOpen(pr.id) && <ul className="pconvs">
                {list.map(c => (
                  <li key={c.id} className={cur && c.id === p.curId ? "on" : ""} onContextMenu={e => showMenu(e, convMenu(pr, c))}>
                    <button className="pick" onClick={() => cur ? p.onOpen(c.id) : p.onOpenOther(pr.id, c.id)} disabled={!cur && !!p.running?.size} title={!cur && p.running?.size ? "Đợi phiên đang chạy xong rồi mới chuyển sang dự án khác" : c.title}>
                      <span className="t">{c.title}{cur && p.locks?.[c.id]?.length ? <span className="clock" title={`Đang giữ khoá:\n${p.locks[c.id].map(l => `${l.target} – ${l.reason}`).join("\n")}`} aria-label={`Đang giữ ${p.locks[c.id].length} khoá`}><LockIcon />{p.locks[c.id].length}</span> : null}</span><small>{p.running?.has(c.id) && <span className="prun" title="Đang chạy" aria-label="Đang chạy" />}<span className={`pagent a-${c.engine}`} title={`Agent: ${AGENT_NAME[c.engine] ?? c.engine}`}>{AGENT_NAME[c.engine] ?? c.engine}</span>{ago(c.updatedAt)}</small>
                    </button>
                    {cur && <span className="acts">
                      <button className="ghost ic-btn" onClick={() => p.onRename(c)} title="Đổi tên" aria-label="Đổi tên">
                        <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M10.5 2.5l3 3L6 13H3v-3z M9 4l3 3" /></svg></button>
                      <button className="ghost ic-btn ic-del" onClick={() => p.onRemove(c.id)} title="Xóa" aria-label="Xóa">
                        <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M2.5 4h11 M6 4V2.5h4V4 M4 4l.7 9.5h6.6L12 4 M6.8 6.5v4.5 M9.2 6.5v4.5" /></svg></button>
                    </span>}
                  </li>
                ))}
                {!list.length && <li className="pempty">Chưa có cuộc trò chuyện</li>}
              </ul>}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/** Cửa sổ "Dự án mới" giữa màn hình: đặt tên, chọn thư mục lưu trên máy (hoặc để tự tạo), chọn file hồ sơ chép vào đó. */
function NewProject({ onCancel, onCreated }: { onCancel: () => void; onCreated: (id: string) => void }) {
  const ref = useRef<HTMLDialogElement>(null);
  const [name, setName] = useState("");
  const [dir, setDir] = useState("");
  const [files, setFiles] = useState<string[]>([]);
  const [busy, setBusy] = useState(""); const [err, setErr] = useState("");
  useEffect(() => { ref.current?.showModal(); }, []);

  const run = async (label: string, fn: () => Promise<void>) => {
    setBusy(label); setErr("");
    try { await fn(); } catch (e) { setErr(niceError(e)); } finally { setBusy(""); }
  };
  const chooseDir = () => run("dir", async () => {
    const d = await pickFolder();
    if (d) { setDir(d); if (!name.trim()) setName(base(d)); }
  });
  const chooseFiles = () => run("files", async () => {
    const f = await pickFiles();
    if (f.length) setFiles(old => [...old, ...f.filter(x => !old.includes(x))]);
  });
  const create = (e: React.FormEvent) => { e.preventDefault(); void run("create", async () => {
    const pr = await createProject(name.trim(), dir);
    if (files.length) await importFiles(pr.id, files);
    onCreated(pr.id);
  }); };
  const autoDir = ["CAD Studio", "projects", name.trim() || "<tên dự án>"].join("\\");

  return (
    <dialog ref={ref} className="dlg pdlg" aria-labelledby="pdlg-t"
      onCancel={e => { e.preventDefault(); if (!busy) onCancel(); }}
      onClick={e => { if (e.target === ref.current && !busy) onCancel(); }}>
      <form onSubmit={create}>
        <div className="pdlg-head">
          <span className="pdlg-ic" aria-hidden="true"><svg viewBox="0 0 16 16"><path d="M1.5 3.5h4l1.5 1.5h7.5v8h-13z" /></svg></span>
          <div>
            <h2 id="pdlg-t">Dự án mới</h2>
            <p>Mỗi dự án là một thư mục trên máy. Hồ sơ bạn đưa vào và file agent tạo ra đều nằm trong đó.</p>
          </div>
        </div>

        <label className="pdlg-lb" htmlFor="pdlg-name">Tên dự án</label>
        <input id="pdlg-name" autoFocus required maxLength={80} value={name} onChange={e => setName(e.target.value)} placeholder="Ví dụ: Tòa A - Lô 12" />

        <span className="pdlg-lb">Thư mục lưu</span>
        <div className="pdlg-pick">
          <div className="pdlg-val">
            {dir ? <code title={dir}>{dir}</code> : <><code>{autoDir}</code><small>Tự tạo mới nếu bạn không chọn</small></>}
          </div>
          {dir && <button type="button" className="ghost" onClick={() => setDir("")} title="Bỏ chọn, dùng thư mục tự tạo">✕</button>}
          <button type="button" disabled={!!busy} onClick={chooseDir}>{busy === "dir" ? "Đang mở…" : "Chọn thư mục…"}</button>
        </div>

        <span className="pdlg-lb">File hồ sơ <small>(không bắt buộc, chép vào thư mục dự án)</small></span>
        <div className="pdlg-files">
          {files.length ? <ul>
            {files.map(f => <li key={f} title={f}><span>{base(f)}</span>
              <button type="button" className="ghost" aria-label={`Bỏ ${base(f)}`} onClick={() => setFiles(l => l.filter(x => x !== f))}>✕</button></li>)}
          </ul> : <p>DWG, DXF, PDF, Excel… của dự án</p>}
          <button type="button" disabled={!!busy} onClick={chooseFiles}>{busy === "files" ? "Đang mở…" : "+ Thêm file…"}</button>
        </div>

        {err && <p className="err-msg" role="alert">{err}</p>}
        <div className="dlg-actions">
          <button type="button" disabled={busy === "create"} onClick={onCancel}>Hủy</button>
          <button type="submit" className="primary" disabled={!!busy || !name.trim()}>{busy === "create" ? "Đang tạo…" : "Tạo dự án"}</button>
        </div>
      </form>
    </dialog>
  );
}

export const LockIcon = () => <svg className="lock-ic" viewBox="0 0 12 12" aria-hidden="true"><rect x="2" y="5" width="8" height="6" rx="1" /><path d="M4 5V3.5a2 2 0 014 0V5" /></svg>;

const size = (b: number) => b >= 1 << 30 ? `${(b / (1 << 30)).toFixed(1)} GB` : b >= 1 << 20 ? `${(b / (1 << 20)).toFixed(1)} MB` : b >= 1024 ? `${Math.round(b / 1024)} KB` : `${b} B`;

/**
 * Hộp "Xóa dự án": mặc định chỉ gỡ khỏi CAD Studio (thư mục giữ nguyên). Tick "Xóa luôn thư mục" thì nút thành
 * "Xóa vĩnh viễn" màu đỏ và phải gõ OK (hoặc confirm) mới bấm được; thư mục được chuyển vào Thùng rác Windows.
 */
export function DeleteProject({ project, onCancel, onDone }: { project: Project; onCancel: () => void; onDone: (recycled: boolean) => void }) {
  const ref = useRef<HTMLDialogElement>(null);
  const [info, setInfo] = useState<DeleteInfo | null>(null);
  const [withFolder, setWithFolder] = useState(false);
  const [typed, setTyped] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  useEffect(() => { ref.current?.showModal(); deleteInfo(project.id).then(setInfo).catch(e => setErr(niceError(e))); }, [project.id]);
  const blocked = !!info?.folderProblem || !info?.exists;
  const ready = !withFolder || ["ok", "confirm"].includes(typed.trim().toLowerCase());   // gõ OK (hoặc confirm) để xác nhận
  const go = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ready || busy) return;
    setBusy(true); setErr("");
    try { const r = await deleteProject(project.id, withFolder); onDone(!!r.recycled); }
    catch (e2) { setErr(niceError(e2)); setBusy(false); }
  };
  return (
    <dialog ref={ref} className="dlg ddlg" aria-labelledby="ddlg-t"
      onCancel={e => { e.preventDefault(); if (!busy) onCancel(); }} onClick={e => { if (e.target === ref.current && !busy) onCancel(); }}>
      <form onSubmit={go}>
        <h2 id="ddlg-t">Xóa dự án "{project.name}" khỏi CAD Studio?</h2>
        <p className="dlg-text">{withFolder
          ? "Xóa dự án, các cuộc trò chuyện và chuyển cả thư mục dự án cùng mọi file trong đó vào Thùng rác Windows."
          : "Xóa dự án và các cuộc trò chuyện khỏi CAD Studio. Thư mục dự án và mọi file trong đó trên máy được giữ nguyên."}</p>
        <div className="ddlg-dir">
          <code title={info?.dir ?? ""}>{info?.dir ?? "…"}</code>
          <small>{!info ? "Đang đếm file…" : !info.exists ? "Thư mục không còn trên máy" : `${info.files}${info.capped ? "+" : ""} file · ${size(info.bytes)}`}</small>
        </div>
        <label className={`ddlg-check${blocked ? " off" : ""}`}>
          <input type="checkbox" checked={withFolder} disabled={blocked || busy} onChange={e => { setWithFolder(e.target.checked); setTyped(""); }} />
          <span>Xóa luôn thư mục dự án và mọi file trong đó
            <small>{info?.folderProblem ?? "Thư mục được chuyển vào Thùng rác, khôi phục được từ đó."}</small></span>
        </label>
        {withFolder && <>
          <label className="ddlg-lb" htmlFor="ddlg-name">Gõ <b>OK</b> để xác nhận</label>
          <input id="ddlg-name" autoFocus autoComplete="off" value={typed} onChange={e => setTyped(e.target.value)} placeholder="OK" />
        </>}
        {err && <p className="err-msg" role="alert">{err}</p>}
        <div className="dlg-actions">
          <button type="button" disabled={busy} onClick={onCancel}>Hủy</button>
          <button type="submit" className={withFolder ? "danger" : "primary"} disabled={busy || !ready}>
            {busy ? "Đang xóa…" : withFolder ? "Xóa vĩnh viễn" : "Xóa dự án"}</button>
        </div>
      </form>
    </dialog>
  );
}
