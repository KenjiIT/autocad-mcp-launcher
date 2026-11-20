import { useEffect, useState } from "react";
import { getClickAction, launchEntry, listProjectFiles, moveEntry, uploadFile, listProjects, newEntry, niceError, pasteEntry, rawUrl, renameEntry, revealFile, searchEntries, trashEntry, type Entry, type Project } from "./api";
import { ContextMenu, type MenuItem } from "./ContextMenu";
import { dialog } from "./Dialog";

const VIEW = /\.(png|jpe?g|gif|webp|svg|pdf|txt|md|csv|json)$/i;
const size = (n: number) => n < 1024 ? `${n} B` : n < 1048576 ? `${(n / 1024).toFixed(0)} KB` : `${(n / 1048576).toFixed(1)} MB`;
const parentOf = (path: string) => path.includes("/") ? path.slice(0, path.lastIndexOf("/")) : "";
const ROOT: Entry = { name: "", path: "", dir: true, size: 0, mtime: 0 };

/** Cột phải kiểu Orca: cây file của thư mục dự án đang chọn (cả file người dùng đưa vào lẫn file agent tạo ra). */
export function FilesPanel({ project, tick }: { project: string; tick: number }) {
  const [info, setInfo] = useState<Project | null>(null);
  const [tree, setTree] = useState<Record<string, Entry[]>>({});
  const [open, setOpen] = useState<Record<string, boolean>>({});
  const [err, setErr] = useState("");
  const [menu, setMenu] = useState<{ x: number; y: number; items: MenuItem[] } | null>(null);
  const [clip, setClip] = useState<Entry | null>(null);                                   // "Sao chép" rồi "Dán" vào thư mục khác
  const [found, setFound] = useState<{ q: string; where: string; list: Entry[] } | null>(null);

  const loadDir = (path: string) => listProjectFiles(project, path).then(r => setTree(t => ({ ...t, [path]: r.entries })));
  const reload = async () => {
    setErr("");
    try {
      const p = (await listProjects()).find(x => x.id === project) ?? null;
      setInfo(p);
      if (p?.dir) await Promise.all(["", ...Object.keys(open).filter(k => open[k])].map(loadDir));
    } catch (e) { setErr(niceError(e)); }
  };
  useEffect(() => { setTree({}); setOpen({}); setClip(null); setFound(null); }, [project]);
  useEffect(() => { void reload(); }, [project, tick]);

  const toggle = (path: string) => {
    const next = !open[path];
    setOpen(o => ({ ...o, [path]: next }));
    if (next) loadDir(path).catch(e => setErr(niceError(e)));
  };
  const act = async (fn: () => Promise<unknown>) => { setErr(""); try { await fn(); } catch (e) { setErr(niceError(e)); } };
  // Bấm vào file: làm theo lựa chọn ở Cài đặt › Mở file — app mặc định của Windows, hỏi app mỗi lần, hoặc xem trên web.
  const openFile = (e: Entry) => {
    const how = getClickAction();
    if (how === "web" && VIEW.test(e.name)) { window.open(rawUrl(project, e.path), "_blank", "noopener"); return; }
    void act(() => launchEntry(project, e.path, how === "choose" ? "choose" : "default"));
  };
  const absPath = (e: Entry) => [info?.dir, ...(e.path ? e.path.split("/") : [])].join("\\");

  /** Tạo tệp/thư mục trong `parent` (rỗng = gốc dự án), rồi mở thư mục đó ra để thấy mục mới. */
  const create = (parent: string, kind: "file" | "dir") => act(async () => {
    const name = (await dialog.prompt(kind === "dir" ? "Tên thư mục mới" : "Tên tệp mới", "", "Tạo"))?.trim();
    if (!name) return;
    await newEntry(project, parent, name, kind);
    if (parent) setOpen(o => ({ ...o, [parent]: true }));
    await loadDir(parent);
  });
  const rename = (e: Entry) => act(async () => {
    const name = (await dialog.prompt(`Đổi tên ${e.dir ? "thư mục" : "tệp"}`, e.name, "Đổi tên"))?.trim();
    if (!name || name === e.name) return;
    await renameEntry(project, e.path, name);
    setOpen(o => { const n = { ...o }; if (n[e.path]) { delete n[e.path]; n[[parentOf(e.path), name].filter(Boolean).join("/")] = true; } return n; });
    await loadDir(parentOf(e.path));
  });
  const remove = (e: Entry) => act(async () => {
    if (!(await dialog.confirm(`Xóa ${e.dir ? "thư mục" : "tệp"} "${e.name}"?`, {
      body: e.dir ? "Thư mục và mọi thứ bên trong được đưa vào Thùng rác của Windows, khôi phục được." : "Tệp được đưa vào Thùng rác của Windows, khôi phục được.",
      okText: "Xóa", danger: true }))) return;
    await trashEntry(project, e.path);
    setOpen(o => { const n = { ...o }; delete n[e.path]; return n; });
    await loadDir(parentOf(e.path));
  });
  const paste = (parent: string) => act(async () => {
    if (!clip) return;
    await pasteEntry(project, clip.path, parent);
    if (parent) setOpen(o => ({ ...o, [parent]: true }));
    await loadDir(parent);
  });
  /** Thu gọn thư mục và mọi thư mục con của nó (gốc = thu gọn hết). */
  const collapse = (path: string) => setOpen(o => Object.fromEntries(Object.entries(o).filter(([k]) => path && k !== path && !k.startsWith(path + "/"))));
  const search = (where: string) => act(async () => {
    const q = (await dialog.prompt(where ? `Tìm trong "${where}"` : "Tìm trong dự án", "", "Tìm"))?.trim();
    if (!q) return;
    setFound({ q, where, list: await searchEntries(project, where, q) });
  });
  const copyText = (text: string) => () => void act(() => navigator.clipboard.writeText(text));

  // ---- Kéo thả: file/thư mục từ Windows -> chép vào dự án; mục trong cây -> chuyển sang thư mục khác ----
  const [dropOn, setDropOn] = useState<string | null>(null);     // thư mục đang được rê lên (rỗng = gốc)
  const [upload, setUpload] = useState<{ done: number; total: number } | null>(null);
  const INNER = "application/x-cad-entry";
  const over = (ev: React.DragEvent, folder: string) => {
    if (!info?.dir) return;
    ev.preventDefault(); ev.stopPropagation();
    ev.dataTransfer.dropEffect = ev.dataTransfer.types.includes(INNER) ? "move" : "copy";
    if (dropOn !== folder) setDropOn(folder);
  };
  /** Gom mọi file trong phần được thả, kể cả thư mục con (đường dẫn tương đối giữ nguyên cấu trúc). */
  const collect = async (entries: any[]): Promise<{ rel: string; file: File }[]> => {
    const out: { rel: string; file: File }[] = [];
    const walk = async (en: any, prefix: string): Promise<void> => {
      if (en.isFile) { const f: File = await new Promise((res, rej) => en.file(res, rej)); out.push({ rel: prefix + f.name, file: f }); return; }
      const reader = en.createReader();
      for (;;) {
        const batch: any[] = await new Promise((res, rej) => reader.readEntries(res, rej));
        if (!batch.length) break;
        for (const c of batch) await walk(c, `${prefix}${en.name}/`);
      }
    };
    for (const en of entries) await walk(en, "");
    return out;
  };
  const drop = (ev: React.DragEvent, folder: string) => {
    if (!info?.dir) return;
    ev.preventDefault(); ev.stopPropagation(); setDropOn(null);
    const inner = ev.dataTransfer.getData(INNER);
    if (inner) {
      if (parentOf(inner) === folder || inner === folder) return;
      void act(async () => { await moveEntry(project, inner, folder); if (folder) setOpen(o => ({ ...o, [folder]: true })); await reload(); });
      return;
    }
    // Phải lấy entries/files NGAY trong sự kiện: sau await trình duyệt xóa sạch dataTransfer.
    const entries = Array.from(ev.dataTransfer.items ?? []).map(i => (i as any).webkitGetAsEntry?.()).filter(Boolean);
    const plain = Array.from(ev.dataTransfer.files).map(f => ({ rel: f.name, file: f }));
    void act(async () => {
      let files = entries.length ? await collect(entries) : [];
      if (!files.length) files = plain;
      if (!files.length) return;
      setUpload({ done: 0, total: files.length });
      try {
        for (const [i, f] of files.entries()) { await uploadFile(project, folder, f.rel, f.file); setUpload({ done: i + 1, total: files.length }); }
      } finally { setUpload(null); }
      if (folder) setOpen(o => ({ ...o, [folder]: true }));
      await reload();
    });
  };

  const showMenu = (ev: React.MouseEvent, items: MenuItem[]) => { ev.preventDefault(); ev.stopPropagation(); setMenu({ x: ev.clientX, y: ev.clientY, items }); };
  /** Menu kiểu VS Code/Orca. Bấm vào tệp thì "thư mục" của các lệnh tạo/dán/tìm là thư mục chứa tệp đó. */
  const entryMenu = (e: Entry): MenuItem[] => {
    const folder = e.dir ? e.path : parentOf(e.path), isRoot = e === ROOT;
    return [
      { label: "Tệp mới", icon: "＋", onClick: () => void create(folder, "file") },
      { label: "Thư mục mới", icon: "▣", onClick: () => void create(folder, "dir") },
      { sep: true },
      ...(!e.dir ? [{ label: "Mở bằng", icon: "↗", sub: [
        ...(VIEW.test(e.name) ? [{ label: "Trình duyệt (tab mới)", onClick: () => window.open(rawUrl(project, e.path), "_blank", "noopener") }] : []),
        { label: "Ứng dụng mặc định của Windows", onClick: () => void act(() => launchEntry(project, e.path, "default")) },
        { label: "Chọn ứng dụng…", onClick: () => void act(() => launchEntry(project, e.path, "choose")) },
      ] as MenuItem[] }] : []),
      ...(!isRoot ? [{ label: "Sao chép", icon: "⧉", hint: "Ctrl+C", onClick: () => setClip(e) }] : []),
      ...(clip ? [{ label: `Dán "${clip.name}"`, icon: "⎘", hint: "Ctrl+V", onClick: () => void paste(folder) }] : []),
      { label: "Sao chép đường dẫn", icon: "⧉", onClick: copyText(absPath(e)) },
      ...(!isRoot ? [{ label: "Sao chép đường dẫn tương đối", icon: "⧉", onClick: copyText(e.path.replace(/\//g, "\\")) }] : []),
      ...(e.dir ? [{ label: "Thu gọn thư mục", icon: "≡", onClick: () => collapse(e.path) }] : []),
      { label: "Tìm trong thư mục", icon: "⌕", onClick: () => void search(folder) },
      { label: "Hiển thị trong File Explorer", icon: "▤", onClick: () => void act(() => revealFile(project, e.path)) },
      ...(!isRoot ? [
        { sep: true } as MenuItem,
        { label: "Đổi tên", icon: "✎", hint: "F2", onClick: () => void rename(e) },
        { label: "Xóa", icon: "✕", hint: "Delete", danger: true, onClick: () => void remove(e) },
      ] : []),
    ];
  };
  const keys = (ev: React.KeyboardEvent, e: Entry) => {
    if (ev.key === "F2") { ev.preventDefault(); void rename(e); }
    else if (ev.key === "Delete") { ev.preventDefault(); void remove(e); }
    else if (ev.ctrlKey && ev.key.toLowerCase() === "c") { ev.preventDefault(); setClip(e); }
    else if (ev.ctrlKey && ev.key.toLowerCase() === "v" && clip) { ev.preventDefault(); void paste(e.dir ? e.path : parentOf(e.path)); }
  };

  const row = (e: Entry, depth: number, label = e.name) => (
    <button type="button" className={`frow${e.dir ? " dir" : ""}${clip?.path === e.path ? " clip" : ""}${e.dir && dropOn === e.path ? " drop" : ""}`} style={{ paddingLeft: 8 + depth * 14 }}
      draggable onDragStart={ev => { ev.dataTransfer.setData(INNER, e.path); ev.dataTransfer.effectAllowed = "move"; }}
      onDragOver={ev => over(ev, e.dir ? e.path : parentOf(e.path))} onDrop={ev => drop(ev, e.dir ? e.path : parentOf(e.path))}
      onContextMenu={ev => showMenu(ev, entryMenu(e))} onKeyDown={ev => keys(ev, e)}
      onClick={() => e.dir ? toggle(e.path) : openFile(e)} title={e.dir ? e.path || e.name : `${e.path} · ${size(e.size)}`}>
      <span className="fic">{e.dir ? (open[e.path] ? "▾" : "▸") : "·"}</span><span className="fname">{label}</span>
    </button>
  );
  const rows = (path: string, depth: number): React.ReactNode =>
    (tree[path] ?? []).map(e => (
      <li key={e.path}>
        {row(e, depth)}
        {e.dir && open[e.path] && <ul>{rows(e.path, depth + 1)}</ul>}
      </li>
    ));

  if (!info) return <aside className="files" aria-label="File dự án">{err && <p className="err-msg small">{err}</p>}</aside>;
  return (
    <aside className={`files${dropOn === "" ? " drop" : ""}`} aria-label="File dự án" onContextMenu={ev => { if (info.dir) showMenu(ev, entryMenu(ROOT)); }}
      onDragOver={ev => over(ev, "")} onDrop={ev => drop(ev, "")}
      onDragLeave={ev => { if (!ev.currentTarget.contains(ev.relatedTarget as Node)) setDropOn(null); }}>
      {menu && <ContextMenu x={menu.x} y={menu.y} items={menu.items} onClose={() => setMenu(null)} />}
      <div className="files-head">
        <b title={info.dir ?? ""}>{info.name}</b>
        {info.dir && <span className="files-acts">
          <button type="button" className="ghost" title="Tìm trong dự án" onClick={() => void search("")}>⌕</button>
          <button type="button" className="ghost" title="Thu gọn tất cả" onClick={() => setOpen({})}>≡</button>
          <button type="button" className="ghost" title="Làm mới" onClick={() => void reload()}>↻</button>
        </span>}
      </div>
      {info.dir ? <>
        {err && <p className="err-msg small" role="alert">{err}</p>}
        {upload && <p className="hint small" role="status">Đang chép file vào dự án… {upload.done}/{upload.total}</p>}
        {found && <div className="ffound">
          <div className="ffound-head"><span>{found.list.length} kết quả cho “{found.q}”{found.where ? ` trong ${found.where}` : ""}</span>
            <button type="button" className="ghost" aria-label="Đóng kết quả tìm" onClick={() => setFound(null)}>✕</button></div>
          <ul className="ftree">{found.list.map(e => <li key={e.path}>{row(e, 0, e.path)}</li>)}</ul>
        </div>}
        <ul className="ftree">{rows("", 0)}</ul>
        {tree[""] && !tree[""].length && <p className="hint small">Thư mục trống. Kéo thả file vào đây, chuột phải để tạo tệp/thư mục, hoặc nhờ agent tạo file.</p>}
      </> : <p className="hint small">Dự án này không gắn thư mục.</p>}
    </aside>
  );
}
