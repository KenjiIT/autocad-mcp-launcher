import { Lightbox } from "./Lightbox";
import { Resizer } from "./Resizer";
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { dialog } from "./Dialog";
import { MAX_IMAGES, prepareImage, type Att } from "./attach";
import { DEFAULT_EFFORT, isEffort, ModelMenu, type Effort } from "./ModelMenu";
import { AskCard, type AskItem } from "./AskCard";
import { CopyButton, Markdown, ProjectCtx } from "./Markdown";
import { collect, SessionPanel } from "./SessionPanel";
import { ProjectTree } from "./ProjectTree";
import { insertSkill, skillPrompt, slashAt, splitSkills } from "./slash";
import { askNotifyPermission, notify } from "./notify";
import { AGENT_NAME, createConv, lastAgent, listAgents, rememberAgent, type Engine, answerAsk, chat, delConv, getQuota, listModels, type Quota, type WinState, WIN_NAME, tightest, listSkills, type ModelInfo, type Usage, NO_USAGE, addUsage, type Skill, fetchImage, getConv, listConvs, newId, niceError, putConv, type Content, type ConvMeta, type CoordLock, listProjects } from "./api";

type Item =
  | { kind: "user"; text: string; images?: Content[] }
  | { kind: "text"; text: string }
  | { kind: "tool"; id: string; name: string; server?: string; input: unknown; done?: boolean; isError?: boolean; content?: Content[] }
  | { kind: "note"; text: string }
  | AskItem;

/** Câu hỏi chưa được trả lời mà lượt chat đã kết thúc (hoặc nạp lại từ bản lưu) thì không còn trả lời được nữa. */
const expireAsks = (list: Item[]): Item[] => list.map(x => (x.kind === "ask" && !x.answers && !x.expired ? { ...x, expired: true } : x));

/** Ảnh: dữ liệu base64 (vừa nhận) hoặc url trên gateway (đã lưu, cần token nên tải bằng fetch). Luôn trả về blob URL để mở/tải được. */
function useImage(c: Content) {
  const [src, setSrc] = useState<string | undefined>();
  const [bad, setBad] = useState(false);
  useEffect(() => {
    let off = false, obj: string | undefined;
    const done = (u: string) => { obj = u; if (!off) setSrc(u); else URL.revokeObjectURL(u); };
    if (c.url) fetchImage(c.url).then(done).catch(() => !off && setBad(true));
    else if (c.data) fetch(`data:${c.mimeType};base64,${c.data}`).then(r => r.blob()).then(b => done(URL.createObjectURL(b))).catch(() => !off && setBad(true));
    return () => { off = true; if (obj) URL.revokeObjectURL(obj); };
  }, [c.url, c.data, c.mimeType]);
  return { src, bad };
}

/** Ảnh chụp từ MCP thường nằm trong canvas lớn hơn cửa sổ AutoCAD, thừa viền đen thuần. Cắt viền đó (chỉ khi thừa đáng kể). */
function useTrimmed(src?: string) {
  const [out, setOut] = useState<string | undefined>();
  useEffect(() => {
    if (!src) return;
    let off = false, obj: string | undefined;
    const im = new Image();
    im.onload = () => {
      const w = im.naturalWidth, h = im.naturalHeight;
      const cv = document.createElement("canvas"); cv.width = w; cv.height = h;
      const g = cv.getContext("2d", { willReadFrequently: true }); if (!g) return;
      g.drawImage(im, 0, 0);
      const px = g.getImageData(0, 0, w, h).data;
      const lit = (x: number, y: number) => { const i = (y * w + x) * 4; return px[i] + px[i + 1] + px[i + 2] > 24; };
      let r = w - 1, b = h - 1, l = 0, t = 0;
      const colLit = (x: number) => { for (let y = 0; y < h; y += 2) if (lit(x, y)) return true; return false; };
      const rowLit = (y: number) => { for (let x = 0; x < w; x += 2) if (lit(x, y)) return true; return false; };
      while (r > 0 && !colLit(r)) r--;
      while (l < r && !colLit(l)) l++;
      while (b > 0 && !rowLit(b)) b--;
      while (t < b && !rowLit(t)) t++;
      const cw = r - l + 1, ch = b - t + 1;
      if (cw * ch > w * h * 0.95 || cw < 50 || ch < 50) return;       // không đáng kể: giữ nguyên ảnh gốc
      const o = document.createElement("canvas"); o.width = cw; o.height = ch;
      o.getContext("2d")!.drawImage(cv, l, t, cw, ch, 0, 0, cw, ch);
      o.toBlob(bl => { if (!bl) return; const u = URL.createObjectURL(bl); if (off) URL.revokeObjectURL(u); else { obj = u; setOut(u); } }, "image/png");
    };
    im.src = src;
    return () => { off = true; if (obj) URL.revokeObjectURL(obj); };
  }, [src]);
  return out ?? src;
}

/** Ảnh nằm trong khung chat (không bị thu gọn), có nút mở ảnh lớn và tải về. */
function Shot({ c }: { c: Content }) {
  const [big, setBig] = useState(false);
  const { src: raw, bad } = useImage(c);
  const src = useTrimmed(raw);
  if (bad) return <p className="hint">Không tải được ảnh.</p>;
  if (!src) return <div className="skel" aria-label="Đang tải ảnh" />;
  const ext = (c.mimeType ?? "image/png").split("/")[1]?.replace("jpeg", "jpg") ?? "png";
  const fname = `autocad-${new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-")}.${ext}`;
  return (
    <figure className="shot">
      {big && <Lightbox src={src} name={fname} onClose={() => setBig(false)} />}
      <button type="button" className="shot-open" onClick={() => setBig(true)} title="Mở ảnh lớn"><img src={src} alt="Ảnh từ AutoCAD" /></button>
      <figcaption>
        <a href={src} onClick={e => { e.preventDefault(); setBig(true); }}>Mở ảnh lớn</a>
        <a href={src} download={fname}>Tải về</a>
      </figcaption>
    </figure>
  );
}

function Img({ c }: { c: Content }) {
  const [big, setBig] = useState(false);
  const { src, bad } = useImage(c);
  if (bad) return <p className="hint">Không tải được ảnh đã lưu.</p>;
  return src ? <>
    <button type="button" className="shot-open" onClick={() => setBig(true)} title="Mở ảnh lớn"><img src={src} alt="Kết quả từ tool" /></button>
    {big && <Lightbox src={src} name="anh.png" onClose={() => setBig(false)} />}
  </> : <div className="skel" aria-label="Đang tải ảnh" />;
}

/** Đếm giây từ lúc tool bắt đầu, để biết nó đang chạy hay đã treo (có tool CAD chạy tới 10 phút). */
function Elapsed() {
  const [s, setS] = useState(0);
  useEffect(() => { const t = setInterval(() => setS(x => x + 1), 1000); return () => clearInterval(t); }, []);
  return <>{s < 60 ? `${s} giây` : `${Math.floor(s / 60)} phút ${s % 60} giây`}</>;
}

function ToolCard({ t }: { t: Extract<Item, { kind: "tool" }> }) {
  // Tool Read chỉ là Claude tự mở lại đúng ảnh đó để xem; ảnh đã hiện ở lần chụp nên không lặp ra ngoài.
  const outside = t.name !== "Read";
  const shots = outside ? t.content?.filter(c => c.type === "image") ?? [] : [];
  // Tool "skills" đang nạp một skill cụ thể thì hiện tên skill thay cho tên server.
  const skill = t.name === "skills" ? (t.input as { name?: unknown } | null)?.name : undefined;
  const tag = typeof skill === "string" && skill ? skill : t.server;
  // coord_claim bị phiên khác giữ khoá: không phải lỗi, hiện thẻ vàng "Chờ <phiên> – <lý do>".
  const first = t.done && !t.isError && t.name === "coord_claim" ? (t.content?.find(c => c.type === "text")?.text ?? "").split("\n")[0] : "";
  const wait = /^busy:\s*(.+)$/.exec(first)?.[1];
  return (
    <>
      <details className={`tool ${t.isError ? "err" : ""}${wait ? " busy" : ""}`}>
        <summary><b className={`dot ${t.done ? (t.isError ? "bad" : wait ? "wait" : "ok") : "run"}`} />{t.name}{tag && <small className="srvtag">{tag}</small>}{wait && <span className="waitmsg">{wait}</span>}<small>{t.done ? (t.isError ? "lỗi" : wait ? "đang bận" : "xong") : <>đang chạy · <Elapsed /></>}</small></summary>
        <div className="tool-copy"><CopyButton text={JSON.stringify(t.input, null, 2)} label="Chép tham số" /></div>
        <pre>{JSON.stringify(t.input, null, 2)}</pre>
        {t.content?.map((c, i) => c.type === "image" ? (outside ? null : <Img key={i} c={c} />) : <pre key={i}>{(c.text ?? "").slice(0, 4000)}</pre>)}
      </details>
      {shots.map((c, i) => <Shot key={c.url ?? i} c={c} />)}
    </>
  );
}

/** Đầu vào của phiên = phần mới + phần đọc từ bộ nhớ đệm + phần ghi vào bộ nhớ đệm (cả ba đều là token Claude phải xử lý). */
const usageIn = (u: Usage) => u.input + u.cacheRead + u.cacheWrite;
/** 950 -> "950", 51.700 -> "51,7k", 6.504.400 -> "6,5m", 2.100.000.000 -> "2,1b". */
const fmtTok = (n: number) => {
  // Ngưỡng tính sau làm tròn một chữ số lẻ, để 999.999 thành "1m" chứ không phải "1.000k".
  const u = n >= 999_950_000 ? [1e9, "b"] : n >= 999_950 ? [1e6, "m"] : n >= 1e3 ? [1e3, "k"] : null;
  return u ? `${(n / (u[0] as number)).toLocaleString("vi-VN", { maximumFractionDigits: 1 })}${u[1]}` : String(n);
};
const pctOf = (w: WinState) => Math.min(100, Math.round((w.used / w.limit!) * 100));
const levelOf = (p: number) => (p >= 100 ? " qbar-full" : p >= 80 ? " qbar-warn" : "");
/** Thời điểm đặt lại, viết ngắn: cùng ngày thì chỉ giờ, khác ngày thì thêm ngày. */
const resetText = (t: number) => {
  const d = new Date(t);
  const sameDay = d.toDateString() === new Date().toDateString();
  return sameDay ? `${d.getHours()}:${String(d.getMinutes()).padStart(2, "0")} hôm nay`
    : d.toLocaleString("vi-VN", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
};

/** Hạn mức token: thanh nhỏ hiện cửa sổ căng nhất; bấm vào mới mở bảng có cả ba cửa sổ 5 giờ / tuần / tháng. */
function QuotaBar({ q }: { q: Quota }) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const lim = q.wins.filter(w => w.limit);
  const top = tightest(q.wins)!;
  const pct = pctOf(top);
  const nf = (n: number) => n.toLocaleString("vi-VN");
  const level = levelOf(pct);

  // Bấm ra ngoài hoặc Esc thì đóng (tooltip mặc định của trình duyệt xấu nên dùng bảng nhỏ tự vẽ).
  useEffect(() => {
    if (!open) return;
    const away = (e: MouseEvent) => { if (!root.current?.contains(e.target as Node)) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", away);
    document.addEventListener("keydown", esc);
    return () => { document.removeEventListener("mousedown", away); document.removeEventListener("keydown", esc); };
  }, [open]);

  return (
    <div className="qwrap" ref={root}>
      <button type="button" className={`qbtn${level}`} aria-expanded={open} onClick={() => setOpen(o => !o)}
        aria-label={`Hạn mức token ${WIN_NAME[top.win]}: đã dùng ${pct} phần trăm. Bấm để xem cả ba mức`}>
        <span className={`qbar${level}`}><i style={{ width: `${pct}%` }} /></span>
        <span className={`qpct${level}`}>{pct}%</span>
      </button>
      {open && (
        <div className="qpop" role="dialog" aria-label="Hạn mức token">
          <p className="qpop-head">Hạn mức token</p>
          {lim.map(w => {
            const p = pctOf(w), lv = levelOf(p);
            return (
              <div className="qpop-win" key={w.win}>
                <p className="qpop-num"><span className="qpop-win-name">Mỗi {WIN_NAME[w.win]}</span> <b>{nf(w.used)}</b> / {nf(w.limit!)} <span className={`qpop-pct${lv}`}>({p}%)</span></p>
                <div className={`qbar qbar-wide${lv}`}><i style={{ width: `${p}%` }} /></div>
                <p className="qpop-reset">{p >= 100 ? "Hết mức — lượt mới bị chặn tới" : "Đặt lại"} {resetText(w.resetAt)}</p>
              </div>
            );
          })}
          <p className="qpop-note">Chạm bất kỳ mức nào là lượt chat mới bị chặn tới khi mức đó đặt lại. Cần thêm thì nhờ quản trị viên nâng hạn mức.</p>
        </div>
      )}
    </div>
  );
}

const usageTip = (u: Usage) =>
  `Đầu vào mới ${u.input.toLocaleString("vi-VN")} · đọc từ bộ nhớ đệm ${u.cacheRead.toLocaleString("vi-VN")} · ghi vào bộ nhớ đệm ${u.cacheWrite.toLocaleString("vi-VN")} · đầu ra ${u.output.toLocaleString("vi-VN")}` +
  (u.costUsd ? ` · chi phí ước tính theo Claude CLI $${u.costUsd.toLocaleString("vi-VN", { maximumFractionDigits: 4 })}` : "");

const ago = (t: number) => {
  const m = Math.round((Date.now() - t) / 60000);
  if (m < 1) return "vừa xong"; if (m < 60) return `${m} phút trước`;
  const h = Math.round(m / 60); if (h < 24) return `${h} giờ trước`;
  return new Date(t).toLocaleDateString("vi-VN");
};

/** Bỏ dấu tiếng Việt và viết thường, để "/pho" khớp cả "phố", "phòng". */
const fold = (t: string) => t.normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/g, "d").replace(/Đ/g, "D").toLowerCase();
/** "thiet-ke-phong-nha" -> "Thiet Ke Phong Nha" (nhãn của chip skill). */
const skillTitle = (name: string) => name.split("-").map(w => w ? w[0].toUpperCase() + w.slice(1) : w).join(" ");
/** Tin của người dùng bắt đầu bằng "/ten-skill" (skill có thật): hiện chip skill rồi phần còn lại. */
function UserText({ text, known }: { text: string; known: { name: string }[] }) {
  const parts = splitSkills(text, known.map(k => k.name));   // skill ở đầu hay giữa câu đều hiện thành chip
  return <>{parts.map((p, i) => "skill" in p ? <span key={i} className="skill-chip in-bubble">{skillTitle(p.skill)}</span> : p.text)}</>;
}
const STARTER = "Phiên chat mới";   // tên phiên chat trống gateway tạo kèm dự án; đổi thành câu hỏi đầu tiên khi gửi

/** Một lượt đang chạy của một phiên (giữ riêng để phiên chạy ngầm khi người dùng mở phiên khác). */
type RunState = { items: Item[]; history: unknown[]; sessionId?: string; usage: Usage; ac: AbortController; model?: string; engine: Engine; effort: Effort };

type ChatProps = {
  epoch: number; project: string; treeKey: number; initialOpen?: string;
  locks?: Record<string, CoordLock[]>;   // khoá đang giữ theo id phiên chat (bảng điều phối)
  onSelectProject: (id: string) => void; onOpenOther: (project: string, conv: string) => void; onTurnStart?: () => void; onTurnDone?: () => void; onProjectsChanged?: () => void;
};
export function Chat({ epoch, project, treeKey, initialOpen, locks, onSelectProject, onOpenOther, onTurnStart, onTurnDone, onProjectsChanged }: ChatProps) {
  const [convs, setConvs] = useState<ConvMeta[]>([]);
  const [curId, setCurIdState] = useState(newId);
  const curIdRef = useRef(curId);
  const setCurId = (id: string) => { curIdRef.current = id; setCurIdState(id); };
  const [items, setItems] = useState<Item[]>([]);
  const [input, setInput] = useState("");
  // Lượt đang chạy theo từng phiên: mỗi phiên chạy độc lập, chuyển sang phiên khác thì phiên cũ vẫn chạy ngầm
  // (stream không bị cắt) và ghi vào bản riêng của nó; quay lại thì thấy tiếp. Mỗi phiên chỉ một lượt một lúc.
  const runs = useRef(new Map<string, RunState>());
  const [, setRunTick] = useState(0);
  const bumpRuns = () => setRunTick(t => t + 1);
  const [listErr, setListErr] = useState("");
  const [skills, setSkills] = useState<Skill[]>([]);
  const [models, setModels] = useState<ModelInfo[]>([]);
  // Mức suy nghĩ lưu theo TỪNG phiên (như model): phiên mới mặc định "Vừa"; phiên người dùng đã chọn mức khác giữ mức đó.
  const [effort, setEffortState] = useState<Effort>(DEFAULT_EFFORT);
  const setEffort = (e: Effort) => { setEffortState(e); if (convsRef.current.some(c => c.id === curIdRef.current)) putConv(curIdRef.current, { effort: e }).catch(() => {}); };
  const [model, setModel] = useState("");                  // model của phiên đang mở; lưu cùng hội thoại
  const [engine, setEngine] = useState<Engine>(() => lastAgent() ?? "cli");   // agent của phiên đang mở (chọn lúc tạo phiên)
  const [usage, setUsageState] = useState<Usage>(NO_USAGE);  // token đã dùng của phiên này
  const usageRef = useRef<Usage>(NO_USAGE);                // bản mới nhất, cho persist() (state trong closure có thể cũ)
  const setUsage = (u: Usage) => { usageRef.current = u; setUsageState(u); };
  const defModel = useRef("");
  const [quota, setQuota] = useState<Quota | null>(null);     // hạn mức token tháng của tài khoản này (null = chưa biết hoặc phiên dịch vụ)
  const refreshQuota = () => { getQuota().then(setQuota).catch(() => setQuota(null)); };
  const [sel, setSel] = useState(0);
  const [menuOff, setMenuOff] = useState(false); // Esc đóng menu tới khi gõ tiếp
  const [failed, setFailed] = useState<string | null>(null);   // tin nhắn vừa gửi lỗi, giữ lại để gửi lại
  const [atts, setAtts] = useState<Att[]>([]);                  // ảnh đang đính vào tin sắp gửi
  const [attErr, setAttErr] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const dropAtts = (list: Att[]) => list.forEach(a => URL.revokeObjectURL(a.preview));
  const addFiles = async (files: File[]) => {
    const imgs = files.filter(f => f.type.startsWith("image/"));
    if (!imgs.length) return;
    const room = MAX_IMAGES - atts.length;
    if (room <= 0) { setAttErr(`Tối đa ${MAX_IMAGES} ảnh mỗi tin nhắn.`); return; }
    const results = await Promise.allSettled(imgs.slice(0, room).map(prepareImage));
    const ok = results.flatMap(r => r.status === "fulfilled" ? [r.value] : []);
    const bad = results.flatMap(r => r.status === "rejected" ? [String(r.reason?.message ?? r.reason)] : []);
    setAttErr(bad[0] ?? (imgs.length > room ? `Chỉ nhận tối đa ${MAX_IMAGES} ảnh, đã bỏ bớt.` : ""));
    if (ok.length) setAtts(p => [...p, ...ok].slice(0, MAX_IMAGES));
  };
  const [sideOpen, setSideOpen] = useState(false);             // màn hình hẹp: mở/đóng danh sách hội thoại
  const itemsRef = useRef<Item[]>([]);
  const history = useRef<unknown[]>([]);        // chế độ API: messages định dạng Anthropic
  const sessionId = useRef<string | undefined>(undefined); // chế độ CLI: nối tiếp phiên cũ
  const busy = runs.current.has(curId);                 // phiên đang mở có lượt đang chạy
  const running = new Set(runs.current.keys());
  const endRef = useRef<HTMLDivElement>(null);
  const taRef = useRef<HTMLTextAreaElement>(null);
  // Ô nhập tự cao lên theo nội dung (tối đa ~8 dòng), gửi xong thì co lại.
  useEffect(() => { const t = taRef.current; if (t) { t.style.height = "auto"; t.style.height = `${Math.min(t.scrollHeight, 200)}px`; } }, [input]);

  // Chỉ tự cuộn khi người dùng đang ở gần đáy. Đang cuộn lên đọc lại thì để yên, và hiện nút "xuống cuối".
  const msgsRef = useRef<HTMLDivElement>(null);
  const [atBottom, setAtBottom] = useState(true);
  const nearBottom = () => {
    const el = msgsRef.current;
    return !el || el.scrollHeight - el.scrollTop - el.clientHeight < 120;
  };
  const toBottom = (smooth = true) => { endRef.current?.scrollIntoView({ block: "end", behavior: smooth ? "smooth" : "auto" }); setAtBottom(true); };

  // Mở một hội thoại cũ: phải cuộn xuống đáy SAU khi nội dung mới đã vẽ xong (queueMicrotask chạy trước lúc React vẽ nên cuộn nhầm nội dung cũ),
  // và giữ ở đáy khi ảnh trong thẻ tool tải xong làm trang dài thêm, cho tới khi người dùng tự cuộn.
  const [openTick, setOpenTick] = useState(0);
  const pinned = useRef(false);
  useLayoutEffect(() => {
    if (!openTick) return;
    pinned.current = true;
    endRef.current?.scrollIntoView({ block: "end", behavior: "instant" }); setAtBottom(true);   // "instant" vì .msgs có scroll-behavior:smooth: mở phiên cũ phải nhảy thẳng xuống đáy, không trượt cả nghìn px
  }, [openTick]);
  const unpin = () => { pinned.current = false; };

  const setAll = (next: Item[]) => { itemsRef.current = next; setItems(next); };
  const push = (fn: (p: Item[]) => Item[]) => {
    const stick = nearBottom();
    setAll(fn(itemsRef.current));
    if (stick) queueMicrotask(() => endRef.current?.scrollIntoView({ block: "end" }));
  };

  // Tiêu đề tab báo khi lượt chạy xong trong lúc người dùng đang ở tab khác.
  useEffect(() => {
    const base = "CAD Studio";
    if (running.size) { document.title = `⏳ Đang chạy… · ${base}`; return; }
    if (!document.hidden || !items.length) { document.title = base; return; }
    document.title = `✓ Xong · ${base}`;
    const back = () => { if (!document.hidden) document.title = base; };
    document.addEventListener("visibilitychange", back);
    return () => { document.removeEventListener("visibilitychange", back); document.title = base; };
  }, [running.size, items.length]);

  // Thư mục dự án đang mở: ảnh agent ghi trong đó và nhắc đường dẫn được hiện ngay trong tin (Markdown.tsx).
  const [projDir, setProjDir] = useState<string | null>(null);
  useEffect(() => { listProjects().then(l => setProjDir(l.find(x => x.id === project)?.dir ?? null)).catch(() => setProjDir(null)); }, [project]);
  const projCtx = useMemo(() => ({ id: project, dir: projDir }), [project, projDir]);

  const refresh = useCallback(() => listConvs().then(c => { setConvs(c); setListErr(""); setConvsLoaded(true); }).catch(e => setListErr(niceError(e))), []);
  useEffect(() => { void refresh(); }, [refresh]);
  useEffect(() => { listSkills().then(setSkills).catch(() => setSkills([])); }, [epoch]);
  useEffect(() => {
    if (!lastAgent()) listAgents().then(r => setEngine(r.default)).catch(() => {});
    refreshQuota();
  }, []);
  // Danh sách model theo agent của phiên; model đang chọn không thuộc agent này thì về mặc định của agent.
  useEffect(() => {
    let live = true;
    listModels(engine).then(r => { if (!live) return; setModels(r.models); defModel.current = r.default; setModel(m => r.models.some(x => x.id === m) ? m : r.default); }).catch(() => live && setModels([]));
    return () => { live = false; };
  }, [engine]);

  // Menu "/": chỉ hiện khi đang gõ token đầu tiên của tin nhắn, ví dụ "/chung" (chưa có dấu cách).
  // "/" ở đầu ô hoặc ngay sau khoảng trắng/xuống dòng, ở bất kỳ đâu trong câu (không tính "/" trong đường dẫn, URL).
  const [caret, setCaret] = useState(0);
  const tok = slashAt(input, caret);
  const slashQ = tok?.query;
  const matches = slashQ === undefined || menuOff ? [] :
    skills.filter(s => fold(s.name + " " + s.description).includes(fold(slashQ)))
      .sort((a, b) => Number(b.name.includes(slashQ)) - Number(a.name.includes(slashQ)));
  const slashRef = useRef<HTMLUListElement>(null);
  useEffect(() => { slashRef.current?.querySelector("li.on")?.scrollIntoView({ block: "nearest" }); }, [sel, matches.length]);
  // Chọn skill: hiện thành "chip" trong ô nhập (như Orca), không để chữ "/ten-skill" lẫn vào câu hỏi.
  const [chip, setChip] = useState<string | null>(null);
  const pickSkill = (name: string) => {
    setSel(0);
    // Chỉ có "/chữ" ở đầu ô (chưa gõ gì khác): thành chip như cũ. Còn lại: chèn "/tên " đúng tại con trỏ, giữ chữ trước và sau.
    if (tok && tok.start === 0 && !chip && !input.slice(caret).trim()) { setChip(name); setInput(""); setCaret(0); taRef.current?.focus(); return; }
    const r = insertSkill(input, caret, name);
    setInput(r.text); setCaret(r.caret); setMenuOff(true);
    requestAnimationFrame(() => { const t = taRef.current; if (t) { t.focus(); t.setSelectionRange(r.caret, r.caret); } });
  };

  const convsRef = useRef(convs); convsRef.current = convs;
  const persist = async (id: string, d: Pick<RunState, "items" | "history" | "sessionId" | "usage" | "model" | "engine" | "effort">) => {
    const firstUser = d.items.find(i => i.kind === "user");
    if (!firstUser) return;
    try {
      await putConv(id, {
        ...(convsRef.current.some(c => c.id === id && c.title !== STARTER) ? {} : { title: (firstUser as { text: string }).text.slice(0, 60) || "Ảnh đính kèm" }),
        items: d.items, history: d.history, sessionId: d.sessionId, model: d.model, engine: d.engine, usage: d.usage, effort: d.effort,
      });
      void refresh();
    } catch (e) { setListErr(`Chưa lưu được cuộc trò chuyện: ${niceError(e)}`); }
  };

  const send = async (override?: string, overrideImgs?: Content[]) => {
    const text = (override ?? (chip ? `/${chip} ${input}` : input)).trim();
    const imgs: Content[] = overrideImgs ?? atts.map(a => ({ type: "image", mimeType: a.mime, data: a.data }));
    const id = curIdRef.current;
    if ((!text && !imgs.length) || runs.current.has(id)) return;   // không gửi 2 lượt cùng lúc trong cùng một phiên
    // "/ten-skill yêu cầu" -> chỉ Claude nạp đúng skill đó trước khi làm; khung chat vẫn hiện nguyên văn bạn gõ.
    // Skill nhắc ở đầu hay giữa câu đều được dặn nạp (xem slash.ts).
    const prompt = skillPrompt(text, skills.map(s => s.name));
    // Có ảnh: nội dung là mảng block kiểu Anthropic (ảnh trước, chữ sau). Gateway kiểm lại rồi chuyển cho từng chế độ chat.
    const content = imgs.length
      ? [...imgs.map(i => ({ type: "image", source: { type: "base64", media_type: i.mimeType, data: i.data } })), { type: "text", text: prompt || "Hãy xem ảnh đính kèm." }]
      : prompt;
    setInput(""); setChip(null); setFailed(null); setAttErr("");
    if (overrideImgs === undefined) { dropAtts(atts); setAtts([]); }
    const ac = new AbortController();
    const run: RunState = { items: itemsRef.current, history: history.current, sessionId: sessionId.current, usage: usageRef.current, ac, model: model || undefined, engine, effort };
    runs.current.set(id, run); bumpRuns();
    // Phiên phải có trong danh sách (kèm tên) ngay khi bắt đầu chạy: người dùng mở phiên khác vẫn thấy và quay lại được.
    const known = convsRef.current.find(c => c.id === id);
    if (!known || known.title === STARTER)
      putConv(id, { title: text.slice(0, 60) || "Ảnh đính kèm", engine, effort, ...(known ? {} : { items: [], history: [] }) }).then(() => refresh()).catch(() => {});
    // Mọi cập nhật của lượt này ghi vào bản riêng của phiên; phiên đang mở thì vẽ ra luôn.
    const up = (fn: (p: Item[]) => Item[]) => { run.items = fn(run.items); if (curIdRef.current === id) push(() => run.items); };
    up(p => [...p, { kind: "user", text, ...(imgs.length ? { images: imgs } : {}) }]);
    queueMicrotask(() => toBottom(false));      // tự gửi thì luôn kéo xuống xem câu trả lời
    onTurnStart?.();
    void askNotifyPermission();   // lần đầu: trình duyệt hỏi cho phép thông báo (cần đúng lúc người dùng vừa bấm gửi)
    let turnError = "";
    try {
      await chat([...run.history, { role: "user", content }], run.sessionId, e => {
        if (e.event === "text") up(p => {
          const last = p[p.length - 1];
          return last?.kind === "text" ? [...p.slice(0, -1), { kind: "text", text: last.text + e.data }] : [...p, { kind: "text", text: e.data }];
        });
        else if (e.event === "tool_use") up(p => [...p, { kind: "tool", ...e.data }]);
        else if (e.event === "tool_result") up(p => p.map(x => x.kind === "tool" && x.id === e.data.id ? { ...x, done: true, isError: e.data.isError, content: e.data.content } : x));
        else if (e.event === "notice") up(p => [...p, { kind: "note", text: e.data }]);
        // Lỗi báo trong luồng (không ném ngoại lệ) cũng là lượt hỏng: giữ tin đã gõ để gửi lại.
        else if (e.event === "error") { up(p => [...p, { kind: "note", text: e.data }]); if (curIdRef.current === id) setFailed(text || "ảnh"); turnError = e.data; }
        else if (e.event === "usage") { run.usage = addUsage(run.usage, e.data); if (curIdRef.current === id) setUsage(run.usage); }
        else if (e.event === "ask") {
          up(p => [...p, { kind: "ask", id: e.data.id, questions: e.data.questions }]);
          notify("CAD Studio cần bạn trả lời", e.data.questions.map(q => q.question).join(" · "), { tag: "cad-ask" });
        }
        else if (e.event === "done") { run.history = e.data.messages; run.sessionId = e.data.sessionId; if (curIdRef.current === id) { history.current = run.history; sessionId.current = run.sessionId; } }
      }, ac.signal, run.model, run.effort, { id, title: (() => { const t = convsRef.current.find(c => c.id === id)?.title; return t && t !== STARTER ? t : text.slice(0, 40) || "Phiên chat"; })() }, run.engine);
    } catch (e) {
      up(p => [...p, { kind: "note", text: ac.signal.aborted ? "Đã dừng. Tin vừa gửi đã đưa lại vào ô soạn tin để sửa và gửi lại." : niceError(e) }]);
      // Dừng giữa chừng (Esc / nút Dừng): đưa tin vừa gửi lại vào ô soạn tin (nếu ô đang trống) để sửa rồi gửi lại, như Claude Code.
      if (ac.signal.aborted && curIdRef.current === id && text) setInput(cur => cur.trim() ? cur : text);
      if (!ac.signal.aborted) { if (curIdRef.current === id) setFailed(text || "ảnh"); turnError = niceError(e); }     // giữ lại tin đã gõ (kèm ảnh) để gửi lại, không bắt gõ lại từ đầu
    } finally {
      run.items = expireAsks(run.items);
      runs.current.delete(id); bumpRuns();
      if (curIdRef.current === id) setAll(run.items);
      refreshQuota(); await persist(id, run); onTurnDone?.();
      if (!ac.signal.aborted) {   // tự bấm Dừng thì không báo
        const last = [...run.items].reverse().find(x => x.kind === "text") as { text: string } | undefined;
        if (turnError) notify("CAD Studio: lượt chat bị lỗi", turnError, { tag: "cad-done" });
        else notify("CAD Studio: agent đã xong", last?.text.replace(/[#*_`>|-]+/g, " ").replace(/\s+/g, " ").trim() || "Xem kết quả trong CAD Studio.", { tag: "cad-done" });
      }
    }
  };

  /** Gửi lại tin nhắn vừa lỗi: bỏ tin của mình và dòng báo lỗi ở cuối, rồi gửi lại nguyên văn. */
  /** Sửa tin cuối của mình: đưa chữ về ô soạn tin, bỏ tin đó cùng mọi thứ sau nó khỏi khung chat (gửi lại thì thành lượt mới). */
  const editLast = (i: number) => {
    const u = itemsRef.current[i];
    if (busy || u?.kind !== "user") return;
    setAll(itemsRef.current.slice(0, i)); setFailed(null); setChip(null);
    setInput(u.text);
    requestAnimationFrame(() => { const t = taRef.current; if (t) { t.focus(); t.setSelectionRange(t.value.length, t.value.length); } });
  };
  // Esc khi agent đang chạy (và không có hộp thoại/menu nào đang mở) thì dừng lượt, như Orca.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape" || !busy || document.querySelector("dialog[open], .cmenu, .slash")) return;
      e.preventDefault();
      runs.current.get(curIdRef.current)?.ac.abort();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [busy]);

  const lastUserIdx = items.map(x => x.kind).lastIndexOf("user");   // chỉ tin cuối của mình mới có nút Sửa
  const retry = () => {
    if (!failed || busy) return;
    const list = [...itemsRef.current];
    while (list.length && list[list.length - 1].kind === "note") list.pop();
    const u = list[list.length - 1];
    let text = failed === "ảnh" ? "" : failed, imgs: Content[] = [];
    if (u?.kind === "user") { text = u.text; imgs = u.images ?? []; list.pop(); }   // gửi lại cả ảnh đã đính, không lấy ảnh đang soạn dở
    setAll(list); setFailed(null);
    void send(text, imgs);
  };

  const reset = (agent: Engine = engine) => {
    rememberAgent(agent);
    const same = agent === engine;
    setEngine(agent);
    // Đang ở một phiên trống sẵn có trong danh sách thì không tạo thêm phiên trống nữa (chỉ đổi agent của nó nếu cần).
    if (!itemsRef.current.length && convs.some(c => c.id === curId)) {
      if (!same) { setModel(""); putConv(curId, { engine: agent }).then(() => refresh()).catch(e => setListErr(niceError(e))); }
      taRef.current?.focus(); return;
    }
    dropAtts(atts); setAtts([]); setAttErr(""); history.current = []; sessionId.current = undefined; setAll([]); setModel(same ? defModel.current : ""); setUsage(NO_USAGE); setEffortState(DEFAULT_EFFORT);
    // Phiên đang chạy (nếu có) vẫn chạy ngầm, không bị dừng.
    const id = newId(); setCurId(id);
    // Tạo phiên ngay (như Orca) để nó hiện trong danh sách; câu hỏi đầu tiên sẽ thành tên phiên.
    putConv(id, { title: STARTER, engine: agent, items: [], history: [] }).then(() => refresh()).catch(e => setListErr(niceError(e)));
    taRef.current?.focus();
  };
  /** Nút + / menu "Phiên chat mới" ở cột dự án: dự án khác thì tạo phiên ở đó rồi chuyển sang. */
  const newIn = (proj: string, agent: Engine) => {
    if (proj === project) { reset(agent); return; }
    rememberAgent(agent);
    const id = newId();
    createConv(proj, id, STARTER, agent).then(() => onOpenOther(proj, id)).catch(e => setListErr(niceError(e)));
  };

  const open = async (id: string) => {
    if (id === curIdRef.current) return;
    const live = runs.current.get(id);   // phiên đang chạy ngầm: lấy bản đang chạy, không lấy bản đã lưu (cũ hơn)
    if (live) {
      history.current = live.history; sessionId.current = live.sessionId;
      setAll(live.items); setCurId(id); setListErr(""); setFailed(null); setUsage(live.usage); setEffortState(live.effort);
      if (live.engine !== engine) { setEngine(live.engine); setModel(live.model ?? ""); } else setModel(live.model ?? defModel.current);
      setOpenTick(t => t + 1); return;
    }
    try {
      const c = await getConv(id);
      history.current = c.history ?? []; sessionId.current = c.sessionId;
      setAll(expireAsks((c.items ?? []) as Item[])); setCurId(id); setListErr(""); setFailed(null);
      setUsage(c.usage ?? NO_USAGE); setEffortState(isEffort(c.effort) ? c.effort : DEFAULT_EFFORT);
      const ce: Engine = c.engine === "codex" || c.engine === "api" ? c.engine : "cli";
      if (ce !== engine) { setEngine(ce); setModel(c.model ?? ""); }   // danh sách model của agent kia tải lại rồi kiểm model
      else setModel(c.model && models.some(m => m.id === c.model) ? c.model : defModel.current);   // model đã lưu bị gỡ khỏi danh sách thì quay về mặc định
      setOpenTick(t => t + 1);
    } catch (e) { setListErr(niceError(e)); }
  };

  // Bấm một cuộc trò chuyện của dự án khác: main đổi dự án rồi dựng lại Chat với initialOpen.
  const opened = useRef(false);
  // Không chỉ định thì mở sẵn phiên chat trống mới nhất (phiên tạo kèm dự án), như Orca mở phiên đang dở.
  const [convsLoaded, setConvsLoaded] = useState(false);
  useEffect(() => {
    if (opened.current || !models.length || !convsLoaded) return;
    const target = initialOpen ?? (convs[0]?.title === STARTER ? convs[0].id : undefined);
    opened.current = true;
    if (target) void open(target);
  }, [models, convsLoaded]);

  const remove = async (id: string) => {
    if (!(await dialog.confirm("Xóa cuộc trò chuyện này?", { body: "Không khôi phục được.", okText: "Xóa", danger: true }))) return;
    try { await delConv(id); if (id === curId) reset(); void refresh(); }
    catch (e) { setListErr(niceError(e)); }
  };

  const rename = async (c: ConvMeta) => {
    const t = (await dialog.prompt("Tên mới cho cuộc trò chuyện", c.title))?.trim();
    if (!t || t === c.title) return;
    try { await putConv(c.id, { title: t }); void refresh(); } catch (e) { setListErr(niceError(e)); }
  };

  return (
    <ProjectCtx.Provider value={projCtx}>
    <div className={`chatwrap${sideOpen ? " side-open" : ""}`}>
      {sideOpen && <div className="side-veil" onClick={() => setSideOpen(false)} aria-hidden="true" />}
      <aside className="convs" aria-label="Các cuộc trò chuyện" onClick={e => { const b = (e.target as HTMLElement).closest("button"); if (b && !b.closest(".sres-head") && !b.classList.contains("sres-row")) setSideOpen(false); }}>
        <ProjectTree key={treeKey} current={project} onSelect={onSelectProject} onOpenOther={onOpenOther}
          convs={convs} locks={locks} curId={curId} busy={busy} running={running} onOpen={id => void open(id)} onRename={c => void rename(c)} onRemove={id => void remove(id)} onNew={newIn} onProjectsChanged={onProjectsChanged} />
        {listErr && <p className="err-msg small" role="alert">{listErr}</p>}
        <SessionPanel res={collect(items)} onShot={i => {
          const el = msgsRef.current?.querySelectorAll(".shot")[i];
          if (el) { unpin(); el.scrollIntoView({ block: "center", behavior: "smooth" }); }
        }} />
        <Resizer name="side" def={260} min={200} max={480} edge="right" />
      </aside>

      <div className={`chat${items.length === 0 ? " fresh" : ""}`}>
        <button className="side-btn" onClick={() => setSideOpen(true)} aria-label="Mở danh sách hội thoại">
          <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M2 4h12M2 8h12M2 12h12" /></svg>
          <span>Hội thoại</span>
        </button>
        <div className="msgs" ref={msgsRef} onScroll={() => setAtBottom(nearBottom())}
          onWheel={unpin} onTouchMove={unpin} onKeyDown={unpin} onPointerDown={unpin}
          onLoadCapture={() => { if (pinned.current) endRef.current?.scrollIntoView({ block: "end", behavior: "instant" }); }}>
          {items.length === 0 && (
            <div className="welcome">
              <h1>Bạn muốn làm gì với bản vẽ?</h1>
              <p>Mô tả việc cần làm, trợ lý sẽ gọi các tool AutoCAD để thực hiện và báo lại từng bước.</p>
            </div>
          )}
          {items.map((it, i) => it.kind === "tool" ? <ToolCard key={i} t={it} /> :
            it.kind === "ask" ? <AskCard key={it.id} item={it} onAnswer={async answers => {
              await answerAsk(it.id, answers);
              const mark = (p: Item[]) => p.map(x => (x.kind === "ask" && x.id === it.id ? { ...x, answers } : x));
              // Phiên đang chạy giữ bản items riêng (RunState); phải ghi câu trả lời vào đó, không thì sự kiện stream kế tiếp
              // vẽ lại từ bản cũ và thẻ hỏi quay về trạng thái chưa trả lời.
              const run = runs.current.get(curIdRef.current);
              if (run) run.items = mark(run.items);
              push(mark);
            }} /> :
            it.kind === "text" ? (
              <div key={i} className="bubble text">
                <Markdown text={it.text} />
                <CopyButton text={it.text} className="copy bubble-copy" />
              </div>
            ) :
            <div key={i} className={`bubble ${it.kind}`} role={it.kind === "note" ? "alert" : undefined}>
              {it.kind === "user" && it.images?.length ? <div className="user-imgs">{it.images.map((c, j) => <Img key={c.url ?? j} c={c} />)}</div> : null}
              {it.kind === "user" ? <UserText text={it.text} known={skills} /> : it.text}
              {it.kind === "user" && !busy && i === lastUserIdx &&
                <button type="button" className="edit-msg" onClick={() => editLast(i)} title="Đưa tin này về ô soạn tin để sửa rồi gửi lại" aria-label="Sửa tin này">Sửa</button>}
              {it.kind === "note" && failed && i === items.length - 1 &&
                <button className="retry" onClick={retry} disabled={busy}>Gửi lại</button>}
            </div>)}
          {busy && items[items.length - 1]?.kind !== "text" && !(items[items.length - 1]?.kind === "ask" && !(items[items.length - 1] as AskItem).answers)
            && <div className="typing" aria-label="Đang xử lý"><span /><span /><span /></div>}
          <div ref={endRef} />
        </div>
        {!atBottom && items.length > 0 && (
          <button className="to-bottom" onClick={() => toBottom()} aria-label="Xuống cuối cuộc trò chuyện" title="Xuống cuối">
            <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 3v10M3.5 8.5 8 13l4.5-4.5" /></svg><span>Mới nhất</span>
          </button>
        )}
        <div className={`composer${dragOver ? " drop" : ""}`}
          onDragOver={e => { if ([...e.dataTransfer.types].includes("Files")) { e.preventDefault(); setDragOver(true); } }}
          onDragLeave={e => { if (!e.currentTarget.contains(e.relatedTarget as Node)) setDragOver(false); }}
          onDrop={e => { setDragOver(false); const fs = Array.from(e.dataTransfer.files); if (fs.length) { e.preventDefault(); void addFiles(fs); } }}>
          {atts.length > 0 && (
            <div className="att-strip" aria-label="Ảnh đính kèm">
              {atts.map(a => (
                <div key={a.id} className="att">
                  <img src={a.preview} alt="Ảnh đính kèm" />
                  <button className="att-x" aria-label="Bỏ ảnh này" title="Bỏ ảnh này"
                    onClick={() => { URL.revokeObjectURL(a.preview); setAtts(p => p.filter(x => x.id !== a.id)); setAttErr(""); }}>×</button>
                </div>
              ))}
            </div>
          )}
          {attErr && <p className="att-err" role="alert">{attErr}</p>}
          {matches.length > 0 && (
            <ul ref={slashRef} className="slash" role="listbox" aria-label="Gợi ý skill">
              {matches.map((s, i) => (
                <li key={s.name} role="option" aria-selected={i === sel} className={i === sel ? "on" : ""}
                  onMouseDown={e => { e.preventDefault(); pickSkill(s.name); }} onMouseEnter={() => setSel(i)}>
                  <b>/{s.name}</b><small>{s.description.split(/[.\-]\s/)[0].slice(0, 110)}</small>
                </li>
              ))}
            </ul>
          )}
          <div className="comp-input">
          {chip && <span className="skill-chip" title={`Dùng skill ${chip}`}>
            <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 1.5 14 4.8v6.4L8 14.5 2 11.2V4.8zM2 4.8l6 3.3 6-3.3M8 8.1v6.4" /></svg>
            {skillTitle(chip)}
            <button type="button" aria-label={`Bỏ skill ${chip}`} onClick={() => { setChip(null); taRef.current?.focus(); }}>×</button>
          </span>}
          <textarea ref={taRef} rows={1} value={input} placeholder={chip ? "" : "Bạn cần làm gì với bản vẽ? Gõ / để chọn skill, dán ảnh (Ctrl+V) để đính kèm"}
            onPaste={e => {
              const fs = Array.from(e.clipboardData.files).filter(f => f.type.startsWith("image/"));
              if (fs.length) { e.preventDefault(); void addFiles(fs); }   // dán chữ thường vẫn như cũ
            }}
            onChange={e => { setInput(e.target.value); setCaret(e.target.selectionStart ?? e.target.value.length); setSel(0); setMenuOff(false); }}
            onSelect={e => setCaret(e.currentTarget.selectionStart ?? 0)}
            onKeyDown={e => {
              if (matches.length) {
                if (e.key === "ArrowDown") { e.preventDefault(); setSel(i => (i + 1) % matches.length); return; }
                if (e.key === "ArrowUp") { e.preventDefault(); setSel(i => (i - 1 + matches.length) % matches.length); return; }
                if (e.key === "Enter" || e.key === "Tab") { e.preventDefault(); pickSkill(matches[sel].name); return; }
                if (e.key === "Escape") { e.preventDefault(); setMenuOff(true); return; }
              }
              if (e.key === "Backspace" && chip && !input) { e.preventDefault(); setChip(null); return; }   // xóa lùi ở đầu ô thì bỏ chip
              if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void send(); }
            }} />
          </div>
          <div className="comp-bar">
            {usageIn(usage) + usage.output > 0
              ? <span className="usage" tabIndex={0} title={usageTip(usage)} aria-label={`Token của phiên này: ${usageTip(usage)}`}>
                  <b>{fmtTok(usageIn(usage) + usage.output)}</b> token<span className="usage-split"> · vào {fmtTok(usageIn(usage))} · ra {fmtTok(usage.output)}</span></span>
              : <span className="comp-hint">Enter gửi · Shift+Enter xuống dòng</span>}
            {quota && tightest(quota.wins) ? <QuotaBar q={quota} /> : null}
            <div className="comp-right">
              <input ref={fileRef} type="file" accept="image/png,image/jpeg,image/webp,image/gif" multiple hidden
                onChange={e => { void addFiles(Array.from(e.target.files ?? [])); e.target.value = ""; }} />
              <button className="attach" onClick={() => fileRef.current?.click()} disabled={busy || atts.length >= MAX_IMAGES}
                aria-label="Đính kèm ảnh" title={`Đính kèm ảnh (tối đa ${MAX_IMAGES}). Cũng có thể dán hoặc kéo thả vào khung chat.`}>
                <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M13.2 7.4 7.7 12.9a3.2 3.2 0 0 1-4.5-4.5l5.6-5.6a2.1 2.1 0 0 1 3 3L6.3 11.3a1 1 0 0 1-1.5-1.5l5-5" /></svg>
              </button>
              <span className={`pagent a-${engine}`} title="Agent của phiên này (chọn lúc tạo phiên ở nút + cạnh dự án)">{AGENT_NAME[engine]}</span>
              {models.length > 0 && <ModelMenu models={models} value={model} onChange={setModel} effort={effort} onEffort={setEffort} disabled={busy} />}
              {busy
                ? <button className="send stop" onClick={() => runs.current.get(curId)?.ac.abort()} aria-label="Dừng" title="Dừng"><svg viewBox="0 0 16 16" aria-hidden="true"><rect x="4" y="4" width="8" height="8" rx="1.5" /></svg></button>
                : <button className="send" onClick={() => void send()} disabled={!input.trim() && !atts.length && !chip} aria-label="Gửi" title="Gửi"><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 13V3M3.5 7.5 8 3l4.5 4.5" /></svg></button>}
            </div>
          </div>
        </div>
        {items.length === 0 && (
          <div className="chips under">
            {([
              ["Vẽ mới", "Vẽ mới: "],
              ["Đo/đọc bản vẽ hiện có", "Đọc bản vẽ đang mở và đo: "],
              ["Bóc khối lượng", "Bóc khối lượng từ bản vẽ đang mở: "],
            ] as const).map(([label, start]) =>
              <button key={label} onClick={() => { setInput(start); taRef.current?.focus(); }}>{label}</button>)}
          </div>
        )}
      </div>
    </div>
    </ProjectCtx.Provider>
  );
}
