/** Lượng token của một lượt gọi Claude. cacheRead/cacheWrite là phần đầu vào đọc từ / ghi vào bộ nhớ đệm. */
export type Usage = { input: number; output: number; cacheRead: number; cacheWrite: number; costUsd?: number };

const num = (v: unknown) => (typeof v === "number" && Number.isFinite(v) && v >= 0 ? v : 0);

/** Chuẩn hóa `usage` của API hoặc của kết quả CLI (cùng tên trường) về Usage. */
export const usageOf = (u: any, costUsd?: unknown): Usage => ({
  input: num(u?.input_tokens), output: num(u?.output_tokens),
  cacheRead: num(u?.cache_read_input_tokens), cacheWrite: num(u?.cache_creation_input_tokens),
  ...(num(costUsd) > 0 ? { costUsd: num(costUsd) } : {}),
});

/** Đọc lại Usage từ dữ liệu do trình duyệt gửi lên: bỏ giá trị lạ để file hội thoại không chứa rác. */
export const cleanUsage = (u: any): Usage | undefined =>
  u && typeof u === "object"
    ? { input: num(u.input), output: num(u.output), cacheRead: num(u.cacheRead), cacheWrite: num(u.cacheWrite), ...(num(u.costUsd) > 0 ? { costUsd: num(u.costUsd) } : {}) }
    : undefined;
