import { createContext, memo, useContext, useMemo, useState } from "react";
import { Lightbox } from "./Lightbox";
import { rawUrl } from "./api";
import { imageRefs, sanitizeSvg, svgDataUrl } from "./svg";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";

/** Sao chép vào clipboard, báo "Đã chép" trong 1,5 giây. Trình duyệt chặn (không phải HTTPS) thì báo lỗi. */
export function useCopy() {
  const [state, setState] = useState<"" | "ok" | "bad">("");
  const copy = async (text: string) => {
    try {
      if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(text);
      else throw new Error("no clipboard");
      setState("ok");
    } catch { setState("bad"); }
    setTimeout(() => setState(""), 1500);
  };
  return { state, copy };
}

export function CopyButton({ text, label = "Sao chép", className = "copy" }: { text: string; label?: string; className?: string }) {
  const { state, copy } = useCopy();
  return (
    <button type="button" className={className} onClick={() => void copy(text)}
      aria-label={state === "ok" ? "Đã chép" : state === "bad" ? "Không chép được" : label} title={label}>
      {state === "ok" ? "Đã chép" : state === "bad" ? "Không chép được" : label}
    </button>
  );
}

/** Khối code: giữ nguyên xuống dòng, có nút sao chép riêng. */
function CodeBlock({ text }: { text: string }) {
  return (
    <div className="md-code">
      <CopyButton text={text} className="copy md-code-copy" />
      <pre><code>{text}</code></pre>
    </div>
  );
}

/**
 * Hiển thị markdown của trợ lý. react-markdown KHÔNG dựng HTML thô trong nội dung (không bật rehype-raw),
 * nên chữ do agent hay tool MCP trả về không chèn được thẻ HTML hay script.
 */
export const Markdown = memo(function Markdown({ text }: { text: string }) {
  return (
    <div className="md">
      <ReactMarkdown
        // remarkBreaks: markdown chuẩn gộp xuống dòng đơn thành dấu cách; trong khung chat thì phải giữ như người dùng thấy.
        remarkPlugins={[remarkGfm, remarkBreaks]}
        components={{
          a: ({ node: _n, ...p }) => <a {...p} target="_blank" rel="noreferrer noopener" />,
          table: ({ node: _n, ...p }) => <div className="md-table"><table {...p} /></div>,
          pre: ({ children }) => {
            // <pre><code>…</code></pre>: lấy chữ gốc để nút sao chép chép đúng nội dung
            const el: any = children;
            const raw = el?.props?.children;
            const code = typeof raw === "string" ? raw.replace(/\n$/, "") : String(raw ?? "");
            // Khối ```svg (hoặc khối bắt đầu bằng <svg): hiện thành hình đã làm sạch
            const lang = String(el?.props?.className ?? "");
            if (/language-svg/.test(lang) || /^\s*<svg[\s>]/i.test(code)) {
              const clean = sanitizeSvg(code);
              if (clean) return <SvgFigure src={svgDataUrl(clean)} name="hinh.svg" code={code} />;
            }
            return <CodeBlock text={code} />;
          },
        }}
      >{text}</ReactMarkdown>
      <ProjectImages text={text} />
    </div>
  );
});

/** Dự án đang mở (id + thư mục): để hiện ảnh agent ghi trong thư mục dự án và nhắc đường dẫn. */
export const ProjectCtx = createContext<{ id: string; dir: string | null } | null>(null);

/** Một hình trong tin: bấm để phóng to, có nút tải về (và xem mã SVG nếu là khối svg). */
function SvgFigure({ src, name, code }: { src: string; name: string; code?: string }) {
  const [big, setBig] = useState(false);
  const [bad, setBad] = useState(false);
  if (bad) return null;   // file chưa có / không đọc được: không hiện khung vỡ
  return (
    <figure className="md-fig">
      <button type="button" className="md-fig-img" onClick={() => setBig(true)} title="Phóng to" aria-label={`Phóng to ${name}`}>
        <img src={src} alt={name} loading="lazy" onError={() => setBad(true)} />
      </button>
      <figcaption>
        <span title={name}>{name}</span>
        <button type="button" className="link" onClick={() => setBig(true)}>Phóng to</button>
        <a href={src} download={name.split("/").pop()}>Tải về</a>
        {code && <CopyButton text={code} label="Chép mã SVG" className="link" />}
      </figcaption>
      {big && <Lightbox src={src} name={name.split("/").pop()} onClose={() => setBig(false)} />}
    </figure>
  );
}

/** Ảnh (.svg/.png/.jpg…) agent nhắc tới trong tin và nằm trong thư mục dự án: hiện luôn bên dưới tin. */
function ProjectImages({ text }: { text: string }) {
  const proj = useContext(ProjectCtx);
  const refs = useMemo(() => imageRefs(text, proj?.dir), [text, proj?.dir]);
  if (!proj || !refs.length) return null;
  return <div className="md-figs">{refs.slice(0, 8).map(p => <SvgFigure key={p} src={rawUrl(proj.id, p)} name={p} />)}</div>;
}
