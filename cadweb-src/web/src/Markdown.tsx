import { memo, useState } from "react";
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
            return <CodeBlock text={typeof raw === "string" ? raw.replace(/\n$/, "") : String(raw ?? "")} />;
          },
        }}
      >{text}</ReactMarkdown>
    </div>
  );
});
