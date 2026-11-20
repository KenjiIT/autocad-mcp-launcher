/** Biến lỗi kỹ thuật thành câu người dùng đọc hiểu được và biết làm gì tiếp. */
export function friendly(e: unknown): string {
  const any = e as any;
  const msg = String(any?.message ?? e);
  const status = any?.status as number | undefined;
  if (any?.code === "ENOENT") return "Không tìm thấy lệnh claude. Cài Claude Code CLI và chạy `claude` để đăng nhập, hoặc chuyển sang chế độ API key trong tab Cài đặt.";
  if (/not logged in|please run \/login|authentication_error|invalid api key|oauth/i.test(msg) && !status) return "Claude CLI chưa đăng nhập. Mở terminal, chạy `claude` rồi đăng nhập, sau đó thử lại.";
  if (/usage limit|rate limit|limit reached/i.test(msg) && !status) return "Đã hết hạn mức của gói Claude trong khung giờ này. Đợi đến khi hạn mức làm mới rồi thử lại.";
  if (status === 401) return "API key không hợp lệ hoặc đã bị thu hồi. Vào tab Cài đặt để nhập lại.";
  if (status === 403) return "API key không có quyền dùng model này. Thử chọn model khác trong tab Cài đặt.";
  if (status === 404 && /model/i.test(msg)) return "Model đã chọn không tồn tại. Chọn model khác trong tab Cài đặt.";
  if (status === 429) return "Đã chạm giới hạn tốc độ hoặc hết hạn mức của API key. Đợi một lát rồi thử lại, hoặc kiểm tra số dư ở console.anthropic.com.";
  if (status === 529 || status === 503 || /overloaded/i.test(msg)) return "Dịch vụ Claude đang quá tải. Thử lại sau ít phút.";
  if (/credit balance|billing/i.test(msg)) return "Tài khoản Anthropic hết số dư. Nạp thêm ở console.anthropic.com.";
  if (/fetch failed|ECONNREFUSED|ECONNRESET|ENOTFOUND|UND_ERR|Connection error/i.test(msg))
    return "Không nối được tới máy chủ. Nếu là server MCP, hãy bật nó hoặc kiểm tra cấu hình ở tab MCP.";
  if (/timed? ?out|timeout/i.test(msg)) return "Tool chạy quá lâu và đã bị ngắt. Thử lại với yêu cầu nhỏ hơn.";
  if (/abort/i.test(msg)) return "Đã dừng.";
  return `Có lỗi không xác định: ${msg}`;
}
