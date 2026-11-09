"""Ghi khối chỉ dẫn "việc AutoCAD thì nạp skill trước" vào tệp chỉ dẫn toàn cục của agent.

Skill đã cài không tự được dùng khi launcher tắt (MCP không kết nối nên không có
hướng dẫn của server). Khối này nằm trong CLAUDE.md / AGENTS.md của tài khoản,
được đánh dấu để cập nhật mà không đụng phần người dùng tự viết.
"""
from pathlib import Path

BEGIN = "<!-- BEGIN autocad-mcp-skills (launcher tự quản lý, đừng sửa trong khối này) -->"
END = "<!-- END autocad-mcp-skills -->"

NOTE = f"""{BEGIN}
## Việc AutoCAD

Mọi việc liên quan đến AutoCAD (vẽ, sửa, đọc, đo, kiểm tra, chép, xuất bản vẽ, vẽ layout, mặt bằng, ranh đất, đặt block), kể cả khi chưa thấy MCP `autocad_beiming` hoặc `autocad_puran` kết nối:

1. Nạp skill `autocad-agent-coordinator` trước khi gọi bất kỳ tool CAD nào, rồi nạp tiếp các skill chuyên biệt khớp trong bảng của skill đó. Không có công cụ Skill thì đọc thẳng tệp `SKILL.md` trong thư mục skill của tài khoản.
2. Yêu cầu mơ hồ hoặc thiếu số liệu: hỏi người dùng một lần, đưa hai lựa chọn "bạn cung cấp số liệu" hoặc "tôi tự vẽ theo giả định nêu rõ".
3. Cần nội thất, cây, cửa, thiết bị: tra skill `autocad-block-library` trước khi vẽ tay.
4. Chưa thấy tool CAD: báo người dùng bật launcher (AutoCAD MCP Launcher) rồi mới tiếp tục, không tự đoán kết quả.
{END}
"""


def install_note(path):
    """Thêm hoặc thay khối chỉ dẫn trong `path`; giữ nguyên phần còn lại. Trả về "added", "updated" hoặc "same"."""
    path = Path(path)
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    start = text.find(BEGIN)
    stop = text.find(END, start) if start != -1 else -1
    if start != -1 and stop != -1:
        stop += len(END)
        if text[stop:stop + 1] == "\n":
            stop += 1
        new = text[:start] + NOTE + text[stop:]
        result = "same" if new == text else "updated"
    else:
        new = text + ("\n" if text and not text.endswith("\n\n") else "") + NOTE
        if text and not text.endswith("\n"):
            new = text + "\n\n" + NOTE
        result = "added"
    if new != text:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(new, encoding="utf-8")
        temporary.replace(path)
    return result
