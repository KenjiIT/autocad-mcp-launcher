---
name: knowledge-lint
description: Kiểm tra sức khỏe kho tri thức chung - đầu trang, liên kết gãy, trang chưa vào mục lục, trang quá hạn, thông tin nhạy cảm lọt vào - và rà trùng lặp, mâu thuẫn giữa các trang. Dùng khi người dùng nói 'kiểm tra kho tri thức', 'lint kho chung', 'có trang nào cũ không', 'trước khi duyệt', hoặc sau khi thêm trang mới vào kho chung.
---

# Kiểm tra kho tri thức chung

Tìm kho theo `knowledge-query`.

## Bước 1: kiểm tra tự động

Trong thư mục kho chạy `python tools/lint.py` (Windows: `py -3 tools/lint.py`; thêm `--strict` để cảnh báo cũng thành lỗi). Script báo:
- đầu trang thiếu hoặc sai (`title`, `type`, `topics`, `status`, `source`, `updated`);
- trang trong `pages/` thiếu `reviewed_by` hoặc còn `draft`; trang trong `proposals/` đã có `reviewed_by`;
- liên kết `[[...]]` gãy, trang chưa có trong `index.md`;
- trang quá một năm chưa cập nhật (cảnh báo);
- nội dung khớp thuật ngữ nhạy cảm (`tools/sensitive-terms.local.txt`) hoặc mẫu email, số điện thoại, đường dẫn máy, khóa.

Lỗi nhạy cảm là mức nghiêm trọng nhất: dừng mọi việc khác, báo người dùng ngay, đừng commit hay push kho cho tới khi sạch.

## Bước 2: rà phần script không làm được

Chỉ làm khi người dùng muốn kiểm tra kỹ, hoặc trước một đợt duyệt. Đọc `index.md`, mở các trang cùng nhóm:
- **Trùng lặp:** hai trang trả lời cùng câu hỏi. Đề xuất gộp.
- **Mâu thuẫn:** hai trang khuyên ngược nhau. Nêu cả hai đoạn, không tự chọn bên nào.
- **Trang quá dài hoặc lẫn hai chủ đề:** đề xuất tách.
- **Lỗi thời:** nội dung nhắc công cụ hay hành vi đã đổi (đối chiếu với mã nguồn hoặc `CAPABILITIES.md` nếu có).
- **Đề xuất tồn đọng:** liệt kê `proposals/` đã nằm lâu, cho người duyệt.

## Báo cáo

Nêu theo thứ tự: lỗi nhạy cảm, lỗi khác, cảnh báo, rồi phát hiện của bước 2. Mỗi mục ghi tệp, vấn đề, cách sửa đề xuất. Chỉ sửa lỗi cơ học (thêm vào `index.md`, sửa liên kết) khi người dùng đồng ý; nội dung trang là việc của người duyệt.
