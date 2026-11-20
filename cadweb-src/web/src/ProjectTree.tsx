import { useEffect, useRef, useState } from "react";
import { createProject, deleteProject, importFiles, listConvs, listProjects, niceError, pickFiles, pickFolder, pinProject, setProjectShell, renameProject, revealFile, type ConvMeta, type Project } from "./api";
import { ContextMenu, type MenuItem } from "./ContextMenu";
import { dialog } from "./Dialog";

const ago = (t: number) => {
  const m = Math.round((Date.now() - t) / 60000);
  return m < 1 ? "vừa xong" : m < 60 ? `${m} phút` : m < 1440 ? `${Math.round(m / 60)} giờ` : `${Math.round(m / 1440)} ngày`;
};
const base = (p: string) => p.split(/[\\/]/).filter(Boolean).pop() ?? p;

type Props = {
  current: string; onSelect: (id: string) => void; onOpenOther: (project: string, conv: string) => void;
  convs: ConvMeta[]; curId: string; busy: boolean;
  onOpen: (id: string) => void; onRename: (c: ConvMeta) => void; onRemove: (id: string) => void; onNew: () => void;
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
      { label: "Phiên chat mới", icon: "+", disabled: p.busy, onClick: () => cur ? p.onNew() : p.onSelect(pr.id) },
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
      { label: "Xóa dự án khỏi CAD Studio", icon: "✕", danger: true, disabled: projects.length < 2, onClick: act(async () => {
        if (!(await dialog.confirm(`Xóa dự án "${pr.name}" khỏi CAD Studio?`, { body: "Xóa các cuộc trò chuyện của dự án. Thư mục dự án và mọi file trong đó trên máy được giữ nguyên.", okText: "Xóa dự án", danger: true }))) return;
        await deleteProject(pr.id);
        const rest = projects.filter(x => x.id !== pr.id);
        await load();
        if (cur && rest[0]) p.onSelect(rest[0].id);
        p.onProjectsChanged?.();
      }) },
    ];
  };
  const convMenu = (pr: Project, c: ConvMeta): MenuItem[] => {
    const cur = pr.id === p.current;
    return [
      { label: "Mở", icon: "↗", onClick: () => cur ? p.onOpen(c.id) : p.onOpenOther(pr.id, c.id) },
      { label: "Đổi tên…", icon: "✎", disabled: !cur, onClick: () => p.onRename(c) },
      { label: "Sao chép tiêu đề", icon: "⧉", onClick: copy(c.title) },
      { sep: true },
      { label: "Xóa phiên chat", icon: "✕", danger: true, disabled: !cur || p.busy, onClick: () => p.onRemove(c.id) },
    ];
  };

  return (
    <div className="ptree">
      {menu && <ContextMenu x={menu.x} y={menu.y} items={menu.items} onClose={() => setMenu(null)} />}
      <div className="ptree-head">
        <span>Dự án</span>
        <button type="button" className="ghost" title="Dự án mới" aria-label="Dự án mới" onClick={() => { setErr(""); setAdding(a => !a); }}>+</button>
      </div>
      {adding && <NewProject onCancel={() => setAdding(false)} onCreated={async id => { setAdding(false); await load(); p.onSelect(id); }} />}
      {err && <p className="err-msg small" role="alert">{err}</p>}
      <div className="ptree-list">
        {projects.map(pr => {
          const cur = pr.id === p.current, list = cur ? p.convs : others[pr.id] ?? [];
          return (
            <div key={pr.id} className={`pnode${cur ? " cur" : ""}`}>
              <div className="prow" onContextMenu={e => showMenu(e, projectMenu(pr))}>
                <button type="button" className="prow-tw" aria-label={isOpen(pr.id) ? "Thu gọn" : "Mở ra"} onClick={() => toggle(pr.id)}>{isOpen(pr.id) ? "▾" : "▸"}</button>
                <button type="button" className="prow-name" title={pr.dir ?? "Không gắn thư mục"} onClick={() => cur ? toggle(pr.id) : p.onSelect(pr.id)}>
                  <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M1.5 3.5h4l1.5 1.5h7.5v8h-13z" /></svg>{pr.name}{pr.pinned && <span className="ppin" title="Đã ghim">●</span>}{pr.shell && <span className="pshell" title="Agent được chạy lệnh trong dự án này">&gt;_</span>}
                </button>
                <button type="button" className="prow-add" title="Cuộc mới trong dự án này" aria-label={`Cuộc mới trong ${pr.name}`}
                  disabled={p.busy} onClick={() => cur ? p.onNew() : p.onSelect(pr.id)}>+</button>
              </div>
              {isOpen(pr.id) && <ul className="pconvs">
                {list.map(c => (
                  <li key={c.id} className={cur && c.id === p.curId ? "on" : ""} onContextMenu={e => showMenu(e, convMenu(pr, c))}>
                    <button className="pick" onClick={() => cur ? p.onOpen(c.id) : p.onOpenOther(pr.id, c.id)} disabled={p.busy && !(cur && c.id === p.curId)} title={c.title}>
                      <span className="t">{c.title}</span><small>{ago(c.updatedAt)}</small>
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
