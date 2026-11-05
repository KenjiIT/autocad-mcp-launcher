---
name: knowledge-capture
description: Ghi điều vừa học được sau một việc (cách đọc bản vẽ, lỗi công cụ và cách sửa, quy tắc thiết kế, quy trình) thành trang đề xuất cho tri thức chung công khai, đã gỡ thông tin dự án và đã đối chiếu bản công khai. Dùng khi người dùng nói 'ghi lại kiến thức', 'lưu kinh nghiệm này', 'đưa vào kho chung', 'đề xuất tri thức', hoặc khi cuối một việc agent thấy có điều không hiển nhiên và dùng lại được; khi đó hỏi người dùng trước khi ghi.
---

# Ghi tri thức mới cho kho chung

Kết quả là **một tệp trong `proposals/`** của thư mục tri thức trên máy. Agent không sửa `wiki/` (launcher ghi đè khi tải) và không sửa repo công khai; người duyệt mới đưa trang vào. Quy ước, đầu trang, đường đi và bảng gỡ thông tin: [references/quy-uoc.md](references/quy-uoc.md). Đọc trước khi viết.

Thư mục tri thức: theo mục "Tìm thư mục tri thức" của skill `knowledge-query`. Chưa có thư mục thì hỏi người dùng nơi đặt; `proposals/` nằm cạnh `wiki/`.

## Có đáng ghi không

Ghi khi cả ba đúng:
- **Không hiển nhiên:** phải mất công mới biết (lỗi lạ, hành vi công cụ, cách đọc khó).
- **Dùng lại được:** áp dụng cho dự án khác, không chỉ dự án này.
- **Chưa có sẵn** trong mã, tài liệu công cụ, `CAPABILITIES.md` hay bản công khai.

Không ghi: số liệu hay quyết định riêng của một dự án (để ở nơi lưu riêng của dự án), trạng thái công việc dở dang, điều suy đoán chưa kiểm chứng.

## Quy trình

1. **Đối chiếu bản công khai trước** (mục cuối của quy ước). Đọc mục lục hiện hành trên mạng, mở trang gần nghĩa. Đã có đủ thì dừng và nói với người dùng là không cần ghi. Có một phần thì chỉ đề xuất phần thiếu, ghi rõ bổ sung cho trang nào.
2. **Chọn loại:** `concept`, `rule`, `howto`, `pitfall`. Một trang một ý; lẫn hai chủ đề thì tách hai trang.
3. **Viết** vào `proposals/<slug>.md` theo đầu trang trong quy ước: `status: draft`, `reviewed_by` trống, `updated` là ngày hôm nay, `source` mô tả nguồn mà không nêu tên dự án. Ngắn, nêu **quy tắc và lý do**, kèm cách kiểm tra khi có.
4. **Gỡ thông tin dự án** theo bảng trong quy ước. Thay bằng ví dụ vô danh.
5. **Chạy lint** bằng skill `knowledge-lint` (`py -3 <skill>/scripts/lint.py --root <thư mục tri thức>`). Sửa đến khi hết lỗi, đặc biệt mục thuật ngữ nhạy cảm.
6. **Báo người dùng:** tên tệp, tóm tắt một dòng, và nói rõ trang **đang chờ duyệt**. Hiện chưa có cổng tự động gửi: người dùng gửi tệp trong `proposals/` cho người duyệt.

## Lưu ý

- Chưa chắc một chi tiết là nhạy cảm hay không thì bỏ chi tiết đó, hoặc hỏi người dùng.
- Người dùng muốn giữ cho riêng dự án thì không ghi ở đây; lưu vào nơi tri thức riêng của dự án.
- Không commit hay push repo công khai.
