// Menu "/" của ô soạn tin, giống Orca/Claude Code: "/" ở đầu ô hoặc ngay sau khoảng trắng/xuống dòng mở menu skill,
// ở BẤT KỲ đâu trong câu. "/" nằm trong đường dẫn/URL (C:/, http://, a/b) thì không mở.
// Tách riêng (không React) để kiểm thử.

/** Token "/chữ" ngay trước con trỏ: vị trí bắt đầu (chỗ dấu "/") và chữ đang gõ sau "/". null nếu không có. */
export function slashAt(text: string, caret: number): { start: number; query: string } | null {
  const before = text.slice(0, caret);
  const m = /(^|\s)\/([\w-]*)$/.exec(before);
  if (!m) return null;
  const start = before.length - m[2].length - 1;
  return { start, query: m[2] };
}

/** Thay "/<chữ đang gõ>" ở con trỏ bằng "/tên " ; giữ nguyên phần trước và sau. Trả chuỗi mới và vị trí con trỏ mới. */
export function insertSkill(text: string, caret: number, name: string): { text: string; caret: number } {
  const t = slashAt(text, caret);
  if (!t) return { text, caret };
  let rest = text.slice(caret);
  rest = rest.replace(/^[\w-]+/, "");            // phần còn dính của chữ đang gõ (con trỏ ở giữa từ)
  const ins = `/${name}` + (rest.startsWith(" ") || rest.startsWith("\n") ? "" : " ");
  return { text: text.slice(0, t.start) + ins + rest, caret: t.start + ins.length + (rest.startsWith(" ") ? 1 : 0) };
}

/** Các skill có thật được nhắc trong tin ("/tên" ở đầu hoặc sau khoảng trắng), theo thứ tự, không trùng. */
export function mentionedSkills(text: string, known: string[]): string[] {
  const out: string[] = [];
  for (const m of text.matchAll(/(^|\s)\/([\w-]+)/g)) if (known.includes(m[2]) && !out.includes(m[2])) out.push(m[2]);
  return out;
}

/**
 * Lời nhắn gửi agent: có skill được nhắc (ở đầu hay giữa câu) thì dặn nạp đúng các skill đó trước khi làm.
 * Skill ở ĐẦU tin: bỏ "/tên" khỏi yêu cầu (như trước). Ở giữa câu: giữ nguyên câu để không mất nghĩa.
 */
export function skillPrompt(text: string, known: string[]): string {
  const names = mentionedSkills(text, known);
  if (!names.length) return text;
  const lead = /^\/([\w-]+)\s*([\s\S]*)$/.exec(text);
  const body = lead && names.includes(lead[1]) ? lead[2].trim() : text;
  const list = names.map(n => `"${n}"`).join(", ");
  const how = names.map(n => `name=${n}`).join("; ");
  return `Hãy dùng skill ${list} (nạp bằng tool skills, operation=get, ${how}) cho yêu cầu sau.\n\n${body || "(Chưa có yêu cầu cụ thể: hãy hỏi tôi cần làm gì.)"}`;
}

/** Tách tin thành đoạn chữ và skill (để hiện skill thành chip ngay trong bong bóng tin, ở bất kỳ vị trí nào). */
export function splitSkills(text: string, known: string[]): ({ text: string } | { skill: string })[] {
  const out: ({ text: string } | { skill: string })[] = [];
  let last = 0;
  for (const m of text.matchAll(/(^|\s)\/([\w-]+)/g)) {
    if (!known.includes(m[2])) continue;
    const at = m.index! + m[1].length;
    if (at > last) out.push({ text: text.slice(last, at) });
    out.push({ skill: m[2] });
    last = at + 1 + m[2].length;
  }
  if (last < text.length) out.push({ text: text.slice(last) });
  return out;
}
