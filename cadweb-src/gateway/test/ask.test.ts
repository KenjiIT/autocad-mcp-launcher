import { test } from "node:test";
import assert from "node:assert/strict";
import { Run, formatAnswers, parseAnswers, parseQuestions, runByToken, runForAnswer } from "../src/ask.js";

const Q = { questions: [
  { question: "Ranh đất là đường nào?", header: "Ranh đất", options: [{ label: "Đường đỏ", description: "màu đỏ" }, { label: "Đường xanh" }] },
  { question: "Làm những phần nào?", header: "Phạm vi", multiSelect: true, options: [{ label: "Tường" }, { label: "Cột" }, { label: "Dầm" }] },
] };

test("kiểm tra câu hỏi agent gửi", () => {
  const ok = parseQuestions(Q);
  assert.ok(Array.isArray(ok) && ok.length === 2 && ok[0].multiSelect === false && ok[1].multiSelect === true);
  for (const bad of [null, {}, { questions: [] }, { questions: [{ question: "x", header: "h", options: [{ label: "a" }] }] },
    { questions: [{ question: "x", header: "h", options: [{ label: "a" }, { label: "a" }] }] },
    { questions: [{ question: "", header: "h", options: [{ label: "a" }, { label: "b" }] }] },
    { questions: Array(5).fill(Q.questions[0]) }])
    assert.equal(typeof parseQuestions(bad), "string", JSON.stringify(bad).slice(0, 60));
});

test("kiểm tra câu trả lời từ trình duyệt", () => {
  const qs = parseQuestions(Q) as ReturnType<typeof Object>;
  assert.ok(Array.isArray(parseAnswers(qs, [{ selected: ["Đường đỏ"] }, { selected: ["Tường", "Cột"] }])));
  assert.ok(Array.isArray(parseAnswers(qs, [{ selected: [], other: "đường vàng" }, { selected: ["Dầm"] }])), "nhập tay thay cho lựa chọn");
  for (const bad of [[{ selected: ["Đường đỏ"] }], "x", [{ selected: ["Không có"] }, { selected: ["Cột"] }],
    [{ selected: ["Đường đỏ", "Đường xanh"] }, { selected: ["Cột"] }], [{ selected: [] }, { selected: ["Cột"] }]])
    assert.equal(typeof parseAnswers(qs, bad), "string", JSON.stringify(bad));
});

test("câu trả lời dạng chữ cho agent", () => {
  const qs = parseQuestions(Q) as any;
  const t = formatAnswers(qs, [{ selected: ["Đường đỏ"] }, { selected: ["Tường", "Cột"], other: "thêm lan can" }]);
  assert.match(t, /Ranh đất là đường nào\? → Đường đỏ/);
  assert.match(t, /Tường; Cột; \(nhập tay\) thêm lan can/);
});

test("hỏi, trả lời đúng chủ thì agent nhận được; sai chủ hoặc sai dữ liệu thì không", async () => {
  const events: any[] = [];
  const run = new Run("user-a", (e, d) => { events.push([e, d]); });
  const ac = new AbortController();
  const p = run.ask(Q, ac.signal);
  const ask = events.find(e => e[0] === "ask")![1];
  assert.equal(ask.questions.length, 2);
  assert.equal(runForAnswer(ask.id, "user-b"), undefined, "người khác không trả lời hộ được");
  assert.equal(runForAnswer(ask.id, "user-a"), run);
  assert.match(run.answer(ask.id, [{ selected: ["Không có"] }, { selected: ["Cột"] }])!, /không thuộc/);
  assert.equal(run.answer(ask.id, [{ selected: ["Đường đỏ"] }, { selected: ["Cột"] }]), null);
  assert.match(await p, /Đường đỏ/);
  assert.equal(runForAnswer(ask.id, "user-a"), undefined, "đã trả lời xong thì hết chờ");
  assert.match(run.answer(ask.id, []) ?? "", /không còn chờ/);
  run.close();
});

test("dừng chat hoặc kết thúc lượt thì câu hỏi đang chờ bị hủy", async () => {
  const run = new Run("u", () => {});
  const ac = new AbortController();
  const p1 = run.ask(Q, ac.signal);
  ac.abort();
  await assert.rejects(p1, /dừng/);
  const p2 = run.ask(Q, new AbortController().signal);
  run.close();
  await assert.rejects(p2, /kết thúc/);
  assert.equal(runByToken(run.token), undefined, "token hết hiệu lực khi lượt chat kết thúc");
  await assert.rejects(new Run("u", () => {}).ask({ questions: [] }, new AbortController().signal), /1 đến 4/);
});

test("luồng SSE đã đóng (ghi báo lỗi) không làm sập gateway", async () => {
  let unhandled: unknown = null;
  const onRej = (e: unknown) => { unhandled = e; };
  process.on("unhandledRejection", onRej);
  try {
    // emit trả về lời hứa bị từ chối, và cả emit ném lỗi đồng bộ
    const r1 = new Run("u", () => Promise.reject(new Error("stream closed")));
    const r2 = new Run("u", () => { throw new Error("stream closed (sync)"); });
    const ac = new AbortController();
    const p1 = r1.ask(Q, ac.signal), p2 = r2.ask(Q, ac.signal);
    ac.abort();
    await assert.rejects(p1, /dừng/); await assert.rejects(p2, /dừng/);
    await new Promise(res => setTimeout(res, 50));      // chờ vòng lặp sự kiện xử lý các lời hứa bị từ chối
    assert.equal(unhandled, null, "không được có unhandled rejection");
    r1.close(); r2.close();
  } finally { process.off("unhandledRejection", onRej); }
});

test("ask-mcp.mjs không được dùng fetch: fetch cắt lời gọi sau 300 giây, người dùng trả lời chậm sẽ bị lỗi", async () => {
  const { readFileSync } = await import("node:fs");
  const src = readFileSync(new URL("../src/ask-mcp.mjs", import.meta.url), "utf8").split("\n").filter(l => !l.trim().startsWith("*") && !l.trim().startsWith("//") && !l.trim().startsWith("/**")).join("\n");
  assert.ok(!/\bfetch\s*\(/.test(src), "dùng node:http, không dùng fetch (UND_ERR_HEADERS_TIMEOUT sau 300 giây)");
  assert.match(src, /http\.request/);
});
