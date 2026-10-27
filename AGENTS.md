# Hướng dẫn cho agent trong dự án này

## Việc AutoCAD

Mọi việc liên quan đến AutoCAD (vẽ, sửa, đọc, đo, kiểm tra, chép, xuất bản vẽ, vẽ layout, mặt bằng, ranh đất, đặt block):

1. **Nạp skill `autocad-agent-coordinator` trước khi gọi bất kỳ tool CAD nào** (MCP `autocad_beiming` hoặc `autocad_puran`). Skill này chứa bảng chọn skill chuyên biệt theo lời người dùng; nạp tiếp các skill khớp trong bảng đó.
2. Khi người dùng yêu cầu vẽ layout và đưa mặt bằng: xác định khu đất, chụp ảnh đưa người dùng xác nhận, rồi mới lập kế hoạch (Quy tắc 1 của skill).
3. Yêu cầu mơ hồ hoặc thiếu số liệu: hỏi người dùng một lần, đưa hai lựa chọn "bạn cung cấp số liệu" hoặc "tôi tự vẽ theo giả định nêu rõ" (Quy tắc 2 của skill).
4. Cần tạo nội thất, cây, cửa, thiết bị: tra thư viện block (`autocad-block-library`) trước khi vẽ tay.

Skill nằm trong `.claude/skills`, `.codex/skills` và `.agents/skills` (ba bản giống nhau). Không có công cụ Skill thì đọc thẳng tệp `SKILL.md` trong thư mục đó.

## Khi tạo hoặc sửa skill

Claude Desktop (chat, Cowork) có kho skill riêng, chỉ nhận skill tải lên dạng zip. Vì vậy mỗi lần tạo hoặc sửa một skill:

1. Sửa đồng bộ ba bản `.claude/skills`, `.codex/skills`, `.agents/skills` (phải giống nhau).
2. Dựng lại zip: `python scripts/build_skill_zips.py <tên-skill>` (không tên thì dựng tất cả; `--skip <tên>` để bỏ qua). Kết quả nằm ở `dist/<tên-skill>.zip`, chứa cả thư mục `references`. Script dừng nếu ba bản không khớp.
3. Báo cho người dùng zip nào cần tải lại lên Claude Desktop (Cài đặt, mục Skills), và chép skill sang thư mục tài khoản (`~/.claude/skills`, `~/.codex/skills`, `~/.agents/skills`) nếu họ muốn áp dụng toàn máy.

## AutoCAD LT

Kết nối LT đi qua `lt-adapter/`, không phải mã gốc trong `autocad-beiming-mcp-custom/`. Muốn biết một tool có chạy trên LT hay không, gọi thao tác chỉ đọc của nó và đọc mã lỗi; nếu phải đọc mã, xem `lt-adapter/` trước.
