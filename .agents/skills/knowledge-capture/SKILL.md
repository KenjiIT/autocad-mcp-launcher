---
name: knowledge-capture
description: Ghi điều vừa học được sau một việc (cách đọc bản vẽ, lỗi công cụ và cách sửa, quy tắc thiết kế, quy trình) thành trang đề xuất cho kho tri thức chung, đã gỡ thông tin dự án. Dùng khi người dùng nói 'ghi lại kiến thức', 'lưu kinh nghiệm này', 'đưa vào kho chung', 'đề xuất tri thức', hoặc khi cuối một việc agent thấy có điều không hiển nhiên và dùng lại được; khi đó hỏi người dùng trước khi ghi.
---

# Ghi tri thức mới vào kho chung

Kết quả của skill này là **một tệp trong `proposals/`** của kho `common-knowledge`. Agent không ghi thẳng vào `pages/`; người duyệt mới chuyển sang `pages/`. Tìm kho theo mục "Tìm kho" của skill `knowledge-query`. Quy ước đầu trang và cách gỡ thông tin: `CONVENTIONS.md` trong kho (đọc trước khi viết).

## Có đáng ghi không

Ghi khi cả ba đúng:
- **Không hiển nhiên:** phải mất công mới biết (lỗi lạ, hành vi công cụ, cách đọc khó).
- **Dùng lại được:** áp dụng cho dự án khác, không chỉ dự án này.
- **Không có sẵn** trong mã, tài liệu công cụ hay `CAPABILITIES.md`.

Không ghi: số liệu hay quyết định riêng của một dự án (để ở nơi lưu riêng của dự án), trạng thái công việc dở dang, điều suy đoán chưa kiểm chứng.

## Quy trình

1. **Tra trước.** Dùng `knowledge-query` xem đã có trang gần nghĩa chưa. Có rồi thì đề xuất bản sửa của trang đó (cùng tên tệp trong `proposals/`, ghi trong nội dung "sửa trang X"), không tạo trang trùng.
2. **Chọn loại:** `concept` (khái niệm, cách đọc), `rule` (quy tắc phải theo), `howto` (các bước), `pitfall` (lỗi và cách tránh). Một trang một ý; lẫn hai chủ đề thì tách hai trang.
3. **Viết** vào `proposals/<slug>.md` theo mẫu đầu trang trong `CONVENTIONS.md`: `status: draft`, `reviewed_by` để trống, `updated` là ngày hôm nay, `source` mô tả nguồn mà không nêu tên dự án. Nội dung ngắn, nêu **quy tắc và lý do**, kèm cách kiểm tra khi có.
4. **Gỡ thông tin dự án** theo bảng trong `CONVENTIONS.md`: tên khách hàng, mã dự án và bản vẽ, số liệu thật, tên người, đường dẫn máy, khóa. Thay bằng ví dụ vô danh.
5. **Chạy lint:** `python tools/lint.py` trong kho (Windows: `py -3 tools/lint.py`). Sửa đến khi sạch lỗi, đặc biệt mục thuật ngữ nhạy cảm.
6. **Báo người dùng:** tên tệp đã tạo, tóm tắt một dòng, và nhắc rằng trang đang chờ duyệt. Ghi một dòng vào `log.md` của kho.

## Lưu ý

- Chưa chắc một chi tiết là nhạy cảm hay không thì bỏ chi tiết đó, hoặc hỏi người dùng.
- Nếu người dùng muốn giữ cho riêng dự án, không ghi vào kho chung; lưu vào nơi tri thức riêng của dự án.
- Không commit hay push kho trừ khi người dùng yêu cầu.
