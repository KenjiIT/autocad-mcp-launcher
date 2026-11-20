import { randomBytes, randomUUID } from "node:crypto";

// Tool `ask_user`: agent hỏi người dùng bằng bảng lựa chọn (giống AskUserQuestion). Dùng chung cho hai chế độ chat:
//  - API: vòng lặp trong chat.ts gọi thẳng run.ask().
//  - CLI: Claude CLI gọi tool MCP `ask_user` của một tiến trình phụ (ask-mcp.mjs), tiến trình đó gọi POST /internal/ask
//    (có token riêng của lượt chat), và bị giữ lại cho tới khi người dùng trả lời trên web.

export type AskOption = { label: string; description?: string };
export type AskQuestion = { question: string; header: string; multiSelect: boolean; options: AskOption[] };
export type AskAnswer = { selected: string[]; other?: string };

export const ASK_TOOL_NAME = "ask_user";
export const ASK_DESCRIPTION =
  "Hỏi người dùng bằng bảng lựa chọn trên giao diện, dùng khi cần họ quyết định giữa vài phương án rời rạc " +
  "(xác nhận ranh đất, chọn hướng làm, có/không). Mỗi câu hỏi có 2-4 lựa chọn ngắn kèm mô tả; người dùng luôn có thể nhập " +
  "câu trả lời khác. Gọi tool này thay vì liệt kê lựa chọn bằng chữ rồi chờ họ gõ. Tối đa 4 câu hỏi mỗi lần.";
export const ASK_SCHEMA = {
  type: "object",
  properties: {
    questions: {
      type: "array", minItems: 1, maxItems: 4,
      items: {
        type: "object",
        properties: {
          question: { type: "string", description: "Câu hỏi đầy đủ, kết thúc bằng dấu hỏi." },
          header: { type: "string", description: "Nhãn rất ngắn (tối đa 12 ký tự) hiện ở đầu câu hỏi." },
          multiSelect: { type: "boolean", description: "true nếu được chọn nhiều đáp án." },
          options: {
            type: "array", minItems: 2, maxItems: 4,
            items: { type: "object", properties: { label: { type: "string" }, description: { type: "string" } }, required: ["label"] },
          },
        },
        required: ["question", "header", "options"],
      },
    },
  },
  required: ["questions"],
} as const;

const str = (v: unknown, max: number) => (typeof v === "string" ? v.trim().slice(0, max) : "");

/** Kiểm tra dữ liệu agent gửi. Trả về danh sách câu hỏi sạch, hoặc chuỗi lỗi để báo lại cho agent. */
export function parseQuestions(input: unknown): AskQuestion[] | string {
  const qs = (input as { questions?: unknown })?.questions;
  if (!Array.isArray(qs) || qs.length < 1 || qs.length > 4) return "questions phải có từ 1 đến 4 câu hỏi.";
  const out: AskQuestion[] = [];
  for (const q of qs) {
    const question = str(q?.question, 400), header = str(q?.header, 24);
    if (!question) return "Mỗi câu hỏi cần có nội dung `question`.";
    const raw = Array.isArray(q?.options) ? q.options : [];
    const options = raw.map((o: any) => ({ label: str(o?.label, 80), description: str(o?.description, 300) || undefined })).filter((o: AskOption) => o.label);
    if (options.length < 2 || options.length > 4) return `Câu hỏi "${question.slice(0, 40)}" cần 2 đến 4 lựa chọn có nhãn.`;
    if (new Set(options.map((o: AskOption) => o.label)).size !== options.length) return `Câu hỏi "${question.slice(0, 40)}" có nhãn lựa chọn bị trùng.`;
    out.push({ question, header: header || "Câu hỏi", multiSelect: q?.multiSelect === true, options });
  }
  return out;
}

/** Kiểm câu trả lời từ trình duyệt: mỗi câu hỏi một mục, nhãn phải thuộc danh sách, chọn một thì không quá một nhãn. */
export function parseAnswers(questions: AskQuestion[], raw: unknown): AskAnswer[] | string {
  if (!Array.isArray(raw) || raw.length !== questions.length) return "Số câu trả lời không khớp số câu hỏi.";
  const out: AskAnswer[] = [];
  for (let i = 0; i < questions.length; i++) {
    const q = questions[i], a = raw[i] as any;
    const selected: string[] = Array.isArray(a?.selected) ? a.selected.filter((x: unknown) => typeof x === "string") : [];
    if (selected.some(l => !q.options.some(o => o.label === l))) return `Có lựa chọn không thuộc câu hỏi ${i + 1}.`;
    if (!q.multiSelect && selected.length > 1) return `Câu hỏi ${i + 1} chỉ được chọn một đáp án.`;
    const other = str(a?.other, 500) || undefined;
    if (!selected.length && !other) return `Câu hỏi ${i + 1} chưa có câu trả lời.`;
    out.push({ selected: [...new Set(selected)], other });
  }
  return out;
}

/** Câu trả lời dạng chữ đưa lại cho agent. */
export const formatAnswers = (questions: AskQuestion[], answers: AskAnswer[]) =>
  "Người dùng đã trả lời:\n" + questions.map((q, i) => {
    const a = answers[i];
    return `- ${q.question} → ${[...a.selected, ...(a.other ? [`(nhập tay) ${a.other}`] : [])].join("; ")}`;
  }).join("\n");

const WAIT_MS = 30 * 60_000;   // quá 30 phút không trả lời thì thôi
const PING_MS = 15_000;        // giữ luồng SSE không bị proxy cắt khi chờ lâu

type Pending = { questions: AskQuestion[]; resolve: (text: string) => void; reject: (e: Error) => void };
const byToken = new Map<string, Run>();
const byAskId = new Map<string, Run>();

/** Một lượt chat đang chạy: nơi giữ các câu hỏi đang chờ người dùng trả lời. */
export class Run {
  readonly token = randomBytes(24).toString("base64url");
  private pending = new Map<string, Pending>();
  constructor(readonly owner: string, private emitRaw: (event: string, data: unknown) => unknown) { byToken.set(this.token, this); }

  /** Ghi xuống luồng SSE. Trình duyệt đã đóng thì việc ghi báo lỗi, phải nuốt lỗi đó: lỗi không ai bắt (unhandled rejection) làm sập cả gateway. */
  private emit(event: string, data: unknown) {
    try { Promise.resolve(this.emitRaw(event, data)).catch(() => {}); } catch { /* luồng đã đóng */ }
  }

  /** Gửi câu hỏi xuống trình duyệt và chờ. Trả về văn bản câu trả lời cho agent. */
  ask(input: unknown, signal: AbortSignal): Promise<string> {
    const qs = parseQuestions(input);
    if (typeof qs === "string") return Promise.reject(new Error(qs));
    if (signal.aborted) return Promise.reject(new Error("Người dùng đã dừng cuộc trò chuyện."));
    const id = randomUUID();
    return new Promise<string>((resolve, reject) => {
      const ping = setInterval(() => { this.emit("ping", ""); }, PING_MS);
      const timer = setTimeout(() => fail(new Error("Người dùng không trả lời trong 30 phút.")), WAIT_MS);
      const onAbort = () => fail(new Error("Người dùng đã dừng cuộc trò chuyện."));
      const done = () => { clearInterval(ping); clearTimeout(timer); signal.removeEventListener("abort", onAbort); this.pending.delete(id); byAskId.delete(id); };
      const fail = (e: Error) => { done(); reject(e); };
      signal.addEventListener("abort", onAbort, { once: true });
      this.pending.set(id, { questions: qs, resolve: t => { done(); resolve(t); }, reject: fail });
      byAskId.set(id, this);
      this.emit("ask", { id, questions: qs });
    });
  }

  /** Trình duyệt trả lời. Trả về chuỗi lỗi nếu không hợp lệ. */
  answer(askId: string, raw: unknown): string | null {
    const p = this.pending.get(askId);
    if (!p) return "Câu hỏi này không còn chờ trả lời.";
    const answers = parseAnswers(p.questions, raw);
    if (typeof answers === "string") return answers;
    p.resolve(formatAnswers(p.questions, answers));
    return null;
  }

  /** Kết thúc lượt chat: mọi câu hỏi còn chờ bị hủy, token hết hiệu lực. */
  close() {
    for (const p of [...this.pending.values()]) p.reject(new Error("Lượt chat đã kết thúc."));
    byToken.delete(this.token);
  }
}

export const runByToken = (token: string | undefined) => (token ? byToken.get(token) : undefined);
/** Tìm lượt chat đang chờ câu hỏi này, chỉ khi đúng chủ sở hữu (người khác không trả lời hộ được). */
export const runForAnswer = (askId: string, owner: string) => { const r = byAskId.get(askId); return r && r.owner === owner ? r : undefined; };
