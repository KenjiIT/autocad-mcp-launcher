import { useState } from "react";

/** Những gì phiên chat này đã tạo ra và đã dùng tới. Suy ra hết từ các item đang hiện, không cần gateway. */
export type Res = {
  shots: { tool: string }[];          // ảnh tool trả về, theo đúng thứ tự .shot trong khung chat
  files: { path: string; tool: string }[];
  uploads: number;                    // ảnh người dùng đính vào
  skills: string[];
  servers: string[];
};

type AnyItem = {
  kind: string;
  name?: string;
  server?: string;
  input?: unknown;
  content?: { type?: string; text?: string }[];
  images?: unknown[];
};

const EXT = "dwg|dxf|pdf|png|jpe?g|webp|xlsx?|csv|txt|md|docx?";
const ENDS = new RegExp(`\\.(${EXT})$`, "i");
/** Đường dẫn nằm lẫn trong văn bản tool trả về (có thể là JSON nên dấu \\ bị nhân đôi). */
const INTEXT = new RegExp(`(?:[A-Za-z]:\\\\{1,2}|\\\\{2,4}|/)[^\\s"'<>|?*\\r\\n]{2,300}\\.(?:${EXT})`, "gi");

const looksPath = (s: string) => s.length < 400 && /[\\/]/.test(s) && ENDS.test(s);
const tidy = (s: string) => s.replace(/\\{2}/g, "\\").trim();
export const baseName = (p: string) => p.split(/[\\/]/).pop() || p;
/** Khoá gộp: cùng một tệp dù viết \ hay /, hoa hay thường. */
export const pathKey = (p: string) => p.replace(/\\/g, "/").replace(/\/{2,}/g, "/").toLowerCase();
/** Nhãn hiển thị: tên tệp; trùng tên (khác đường dẫn) thì thêm thư mục cha, ví dụ "thiet-ke-phong-nha/SKILL.md". */
export function fileLabels(paths: string[]): string[] {
  const count = new Map<string, number>();
  for (const p of paths) { const b = baseName(p).toLowerCase(); count.set(b, (count.get(b) ?? 0) + 1); }
  return paths.map(p => {
    const parts = p.split(/[\\/]/).filter(Boolean);
    return (count.get(baseName(p).toLowerCase()) ?? 0) > 1 && parts.length > 1 ? parts.slice(-2).join("/") : baseName(p);
  });
}

/** Quét mọi chuỗi trong tham số tool (quét giá trị thật, không quét JSON, để không phải lo dấu thoát). */
function walk(v: unknown, out: string[], depth = 0) {
  if (depth > 6 || out.length > 120) return;
  if (typeof v === "string") { const t = v.trim(); if (looksPath(t)) out.push(t); return; }
  if (Array.isArray(v)) { for (const x of v) walk(x, out, depth + 1); return; }
  if (v && typeof v === "object") { for (const x of Object.values(v as object)) walk(x, out, depth + 1); }
}

export function collect(items: readonly unknown[]): Res {
  const shots: Res["shots"] = [];
  const files: Res["files"] = [];
  const seen = new Set<string>();
  const skills: string[] = [];
  const servers: string[] = [];
  let uploads = 0;

  for (const raw of items) {
    const it = raw as AnyItem;
    if (it.kind === "user") { uploads += it.images?.length ?? 0; continue; }
    if (it.kind !== "tool") continue;
    const tool = it.name ?? "tool";

    // Ảnh: đúng những ảnh ToolCard vẽ ra ngoài (tool Read chỉ xem lại ảnh đã có).
    if (tool !== "Read") for (const c of it.content ?? []) if (c.type === "image") shots.push({ tool });

    if (it.server && !servers.includes(it.server)) servers.push(it.server);
    if (tool === "skills") {
      const i = it.input as { operation?: unknown; name?: unknown } | null;
      if (i?.operation === "get" && typeof i.name === "string" && i.name && !skills.includes(i.name)) skills.push(i.name);
    }

    const found: string[] = [];
    walk(it.input, found);
    for (const c of it.content ?? []) {
      if (c.type === "image" || !c.text) continue;
      for (const m of c.text.slice(0, 20000).matchAll(INTEXT)) found.push(m[0]);
    }
    for (const p0 of found) {
      const p = tidy(p0);
      const k = pathKey(p);
      if (!p || seen.has(k)) continue;
      seen.add(k);
      files.push({ path: p, tool });
    }
  }
  return { shots, files, uploads, skills, servers };
}

export const resEmpty = (r: Res) => !r.shots.length && !r.files.length && !r.uploads && !r.skills.length && !r.servers.length;

function Copyable({ path, label }: { path: string; label: string }) {
  const [ok, setOk] = useState(false);
  return (
    <button type="button" className="sres-row" title={`${path}\nBấm để chép đường dẫn`}
      onClick={() => { void navigator.clipboard.writeText(path).then(() => { setOk(true); setTimeout(() => setOk(false), 1200); }); }}>
      <span className="sres-name">{label}</span>
      <small className="sres-tag">{ok ? "đã chép" : (baseName(path).split(".").pop() ?? "").toLowerCase()}</small>
    </button>
  );
}

/** Bảng "phiên này" nằm dưới danh sách hội thoại, thu gọn được. */
export function SessionPanel({ res, onShot }: { res: Res; onShot: (i: number) => void }) {
  const [open, setOpen] = useState(true);
  if (resEmpty(res)) return null;
  return (
    <section className="sres" aria-label="Tài nguyên của phiên này">
      <button type="button" className="sres-head" aria-expanded={open} onClick={() => setOpen(o => !o)}>
        <span>Trong phiên này</span>
        <svg className={`sres-caret${open ? " sres-up" : ""}`} viewBox="0 0 16 16" aria-hidden="true"><path d="M4 10l4-4 4 4" /></svg>
      </button>
      {open && (
        <div className="sres-body">
          {res.shots.length > 0 && (
            <div className="sres-group">
              <p className="sres-cap">Ảnh trả về ({res.shots.length})</p>
              {res.shots.slice(-8).map((s, i, a) => {
                const idx = res.shots.length - a.length + i;
                return (
                  <button key={idx} type="button" className="sres-row" onClick={() => onShot(idx)} title="Cuộn tới ảnh này">
                    <span className="sres-name">Ảnh {idx + 1}</span><small className="sres-tag">{s.tool}</small>
                  </button>
                );
              })}
            </div>
          )}
          {res.files.length > 0 && (
            <div className="sres-group">
              <p className="sres-cap">Tệp đã nhắc tới ({res.files.length})</p>
              {(() => {
                const shown = res.files.slice(-10), labels = fileLabels(shown.map(f => f.path));
                return shown.map((f, i) => <Copyable key={pathKey(f.path)} path={f.path} label={labels[i]} />);
              })()}
            </div>
          )}
          <div className="sres-group">
            <p className="sres-cap">Đã dùng</p>
            {res.uploads > 0 && <p className="sres-line">Ảnh đính kèm <b>{res.uploads}</b></p>}
            {res.servers.length > 0 && <p className="sres-line">MCP <b>{res.servers.join(", ")}</b></p>}
            {res.skills.length > 0 && <p className="sres-line">Skill <b>{res.skills.join(", ")}</b></p>}
            {!res.uploads && !res.servers.length && !res.skills.length && <p className="sres-line sres-mute">Chưa có</p>}
          </div>
        </div>
      )}
    </section>
  );
}
