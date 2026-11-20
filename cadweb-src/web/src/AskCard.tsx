import { useState } from "react";
import { niceError, type AskAnswer, type AskQuestion } from "./api";

export type AskItem = { kind: "ask"; id: string; questions: AskQuestion[]; answers?: AskAnswer[]; expired?: boolean };

type Draft = { selected: string[]; other: string; otherOn: boolean };

const summary = (a: AskAnswer) => [...a.selected, ...(a.other ? [a.other] : [])].join("; ");

/** Bảng lựa chọn khi agent hỏi (tool ask_user): chọn đáp án hoặc nhập câu trả lời khác, rồi gửi. */
export function AskCard({ item, onAnswer }: { item: AskItem; onAnswer: (answers: AskAnswer[]) => Promise<void> }) {
  const [draft, setDraft] = useState<Draft[]>(() => item.questions.map(() => ({ selected: [], other: "", otherOn: false })));
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const locked = !!item.answers || !!item.expired;

  const set = (i: number, f: (d: Draft) => Draft) => setDraft(ds => ds.map((d, j) => (j === i ? f(d) : d)));
  const toggle = (i: number, q: AskQuestion, label: string) => set(i, d => {
    if (q.multiSelect) return { ...d, selected: d.selected.includes(label) ? d.selected.filter(x => x !== label) : [...d.selected, label] };
    return { ...d, selected: [label], otherOn: false };           // chọn một: bỏ chế độ nhập tay
  });
  const toggleOther = (i: number, q: AskQuestion) => set(i, d => q.multiSelect ? { ...d, otherOn: !d.otherOn } : { ...d, selected: [], otherOn: true });

  const answers: AskAnswer[] = draft.map(d => ({ selected: d.selected, ...(d.otherOn && d.other.trim() ? { other: d.other.trim() } : {}) }));
  const ready = answers.every(a => a.selected.length > 0 || a.other);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ready || busy) return;
    setBusy(true); setErr("");
    try { await onAnswer(answers); } catch (x) { setErr(niceError(x)); } finally { setBusy(false); }
  };

  if (locked) return (
    <div className="ask-card ask-done" role="group" aria-label="Câu hỏi của agent">
      {item.questions.map((q, i) => (
        <p key={i} className="ask-sum"><span className="ask-chip">{q.header}</span> {q.question}
          <b>{item.answers ? summary(item.answers[i]) : "Chưa trả lời (câu hỏi đã hết hạn)"}</b></p>
      ))}
    </div>
  );

  return (
    <form className="ask-card" onSubmit={submit} role="group" aria-label="Câu hỏi của agent">
      {item.questions.map((q, i) => (
        <fieldset key={i} className="ask-q">
          <legend><span className="ask-chip">{q.header}</span> {q.question}</legend>
          {q.multiSelect && <p className="ask-hint">Chọn một hoặc nhiều đáp án</p>}
          <div className="ask-opts">
            {q.options.map(o => {
              const on = draft[i].selected.includes(o.label);
              return (
                <label key={o.label} className={`ask-opt${on ? " on" : ""}`}>
                  <input type={q.multiSelect ? "checkbox" : "radio"} name={`ask-${item.id}-${i}`} checked={on} onChange={() => toggle(i, q, o.label)} />
                  <span className={`ask-mark${q.multiSelect ? " sq" : ""}`} aria-hidden="true" />
                  <span><b>{o.label}</b>{o.description && <small>{o.description}</small>}</span>
                </label>
              );
            })}
            <label className={`ask-opt${draft[i].otherOn ? " on" : ""}`}>
              <input type={q.multiSelect ? "checkbox" : "radio"} name={`ask-${item.id}-${i}`} checked={draft[i].otherOn} onChange={() => toggleOther(i, q)} />
              <span className={`ask-mark${q.multiSelect ? " sq" : ""}`} aria-hidden="true" />
              <span><b>Khác</b><small>Nhập câu trả lời của bạn</small></span>
            </label>
            {draft[i].otherOn && (
              <input className="ask-other" autoFocus maxLength={500} placeholder="Nhập câu trả lời…" aria-label={`Câu trả lời khác cho: ${q.question}`}
                value={draft[i].other} onChange={e => set(i, d => ({ ...d, other: e.target.value }))} />
            )}
          </div>
        </fieldset>
      ))}
      <div className="ask-bar">
        <button className="primary" disabled={!ready || busy}>{busy ? "Đang gửi…" : "Gửi câu trả lời"}</button>
        <span className="err-msg small" role="alert">{err}</span>
      </div>
    </form>
  );
}
