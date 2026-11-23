// Khối "skill hiện có" chèn vào system prompt mỗi lượt (Claude CLI, Codex, Claude API): agent biết có những skill nào
// và phải nạp skill khớp việc rồi đi đúng lộ trình của nó trước khi dựng/vẽ. Giữ gọn: cắt mô tả, giới hạn tổng độ dài.

export type SkillInfo = { name: string; description: string };

const DESC_MAX = 110;     // ký tự mỗi mô tả
const TOTAL_MAX = 3500;   // ký tự cả khối

const short = (t: string) => {
  const one = t.replace(/\s+/g, " ").trim();
  return one.length > DESC_MAX ? one.slice(0, DESC_MAX - 1).replace(/\s+\S*$/, "") + "…" : one;
};

/** Khối lời dặn + danh sách skill; rỗng khi không có skill (ví dụ tool skills không được phép). */
export function skillsNote(list: SkillInfo[]): string {
  if (!list.length) return "";
  const head =
    "Bộ skill nghiệp vụ hiện có (nạp bằng tool `skills` của MCP: operation=get, name=<tên>; tệp tham chiếu: thêm path). " +
    "TRƯỚC KHI LÀM: nếu yêu cầu khớp skill nào thì nạp skill đó ngay và đi đúng lộ trình của nó (hỏi đủ thông tin, đưa phương án, " +
    "các phép kiểm tra…) trước khi dựng hay vẽ. Nhiều skill khớp thì nạp skill điều phối/chuyên sâu phù hợp nhất (và skill nó chỉ tới). " +
    "Không bỏ bước của skill vì muốn nhanh.\nDanh sách:";
  const lines: string[] = [];
  let used = head.length;
  for (const s of list) {
    const line = `- ${s.name}: ${short(s.description)}`;
    if (used + line.length + 1 > TOTAL_MAX) { lines.push(`- … và ${list.length - lines.length} skill khác (xem bằng skills operation=list)`); break; }
    lines.push(line); used += line.length + 1;
  }
  return `${head}\n${lines.join("\n")}`;
}
