---
name: knowledge-lint
description: Kiểm tra thư mục tri thức chung (wiki đã tải về và proposals chờ duyệt) - đầu trang, liên kết gãy, trang chưa vào mục lục, trang quá hạn, thông tin nhạy cảm lọt vào - rồi rà trùng lặp và mâu thuẫn giữa các trang. Dùng khi người dùng nói 'kiểm tra kho tri thức', 'lint kho chung', 'có trang nào cũ không', 'trước khi gửi đề xuất', hoặc sau khi viết trang mới vào proposals.
---

# Kiểm tra tri thức chung

Thư mục tri thức: theo `knowledge-query` (mặc định `~/autocad-knowledge`, có `wiki/` và `proposals/`).

## Bước 1: kiểm tra tự động

```
py -3 <thư mục skill>/scripts/lint.py --root <thư mục tri thức>
```

Thêm `--strict` để cảnh báo cũng thành lỗi. Script báo:
- **proposals/:** thiếu hoặc sai đầu trang (`title`, `type`, `topics`, `status`, `source`, `updated`); đã có `reviewed_by` hoặc không phải `draft`;
- **wiki/:** trang chưa có trong `wiki/index.md`; trang có đầu trang nhưng thiếu `reviewed_by`; trang quá một năm chưa cập nhật (cảnh báo). Các trang công khai hiện có chưa có đầu trang nên chỉ bị cảnh báo;
- liên kết `[[...]]` gãy;
- nội dung khớp thuật ngữ nhạy cảm hoặc mẫu email, số điện thoại, đường dẫn máy, khóa.

Danh sách thuật ngữ nhạy cảm riêng nằm ở `<thư mục tri thức>/sensitive-terms.local.txt` (một dòng một thuật ngữ: mã dự án, tên khách hàng, địa chỉ). Không có file này thì lint chỉ quét mẫu chung và in lưu ý. Nếu người dùng đang làm dự án có mã riêng, đề nghị tạo file trước khi gửi đề xuất. Không bao giờ đưa file này lên repo công khai.

Lỗi nhạy cảm là mức nghiêm trọng nhất: dừng mọi việc khác, báo người dùng ngay, đừng gửi đề xuất cho tới khi sạch.

Lưu ý: `wiki/` bị launcher ghi đè khi bấm **Tải tri thức**, nên lỗi ở `wiki/` là việc của người duyệt repo công khai, không sửa tại chỗ.

## Bước 2: rà phần script không làm được

Chỉ làm khi người dùng muốn kiểm tra kỹ. Đọc `wiki/index.md`, mở các trang cùng nhóm:
- **Trùng lặp:** hai trang trả lời cùng câu hỏi. Đề xuất gộp.
- **Mâu thuẫn:** hai trang khuyên ngược nhau. Nêu cả hai đoạn, không tự chọn bên nào.
- **Trang quá dài hoặc lẫn hai chủ đề:** đề xuất tách.
- **Lỗi thời:** nội dung nhắc công cụ hay hành vi đã đổi (đối chiếu với mã nguồn hoặc `CAPABILITIES.md` nếu có).
- **Đề xuất tồn đọng:** liệt kê `proposals/` đã nằm lâu, cho người duyệt.
- **Đề xuất trùng bản công khai:** đối chiếu với mục lục trên mạng (xem quy ước của `knowledge-capture`).

## Báo cáo

Nêu theo thứ tự: lỗi nhạy cảm, lỗi khác, cảnh báo, rồi phát hiện của bước 2. Mỗi mục ghi tệp, vấn đề, cách sửa đề xuất. Chỉ sửa lỗi cơ học trong `proposals/` khi người dùng đồng ý; nội dung trang công khai là việc của người duyệt.
