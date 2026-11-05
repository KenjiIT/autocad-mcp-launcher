---
name: knowledge-promote
description: Chuyển một trang tri thức riêng của dự án (ví dụ trong .llmwiki/wiki hoặc nơi lưu tri thức riêng của dự án) thành bản chung đã gỡ thông tin nhạy cảm, đưa vào hàng chờ duyệt của kho tri thức chung. Dùng khi người dùng nói 'đưa lên kho chung', 'chuyển thành tri thức chung', 'gỡ tên dự án rồi chia sẻ', 'promote', 'trang này dùng chung được không'.
---

# Chuyển tri thức riêng thành tri thức chung

Trang riêng của dự án có thể chứa thông tin không được chia sẻ. Skill này tách phần **quy tắc dùng lại được** khỏi phần **dữ kiện riêng**, và chỉ đưa phần đầu vào `proposals/` của kho `common-knowledge`. Tìm kho theo `knowledge-query`; quy ước và bảng gỡ thông tin ở `CONVENTIONS.md` trong kho.

## Quy trình

1. **Đọc trang nguồn** và đánh dấu từng đoạn thuộc loại nào:
   - *Chung:* quy tắc, lý do, cách kiểm tra, hành vi công cụ, cách đọc loại bản vẽ.
   - *Riêng:* tên khách hàng và dự án, mã bản vẽ và lô, số liệu thật (kích thước, diện tích, số căn, tọa độ), kết quả đánh giá một bản vẽ cụ thể, tên người, đường dẫn máy.
2. **Lập bảng gỡ** và đưa người dùng xem trước khi ghi: cột trái là đoạn nguồn, cột phải là "giữ nguyên", "viết lại thành ví dụ vô danh", hoặc "bỏ". Trang nói chủ yếu về một dự án cụ thể (trang entity, đánh giá một bản vẽ) thường chỉ rút được vài quy tắc; nói thẳng nếu gần như không có gì chung để chuyển.
3. **Viết bản chung** vào `proposals/<slug>.md` theo mẫu đầu trang: `status: draft`, `reviewed_by` trống, `source` mô tả nguồn mà không nêu tên dự án. Dùng ví dụ vô danh ("một dự án căn hộ", "dầm dài gần 30 m"). Số liệu chỉ giữ khi cần cho ý, ở dạng khoảng.
4. **Kiểm tra hai lớp:**
   - Chạy `python tools/lint.py` trong kho (Windows: `py -3 tools/lint.py`).
   - Đọc lại bản chung từ đầu, tìm thứ mà danh sách không bắt được: tên viết tắt, biệt danh dự án, chi tiết đủ để suy ra dự án nào.
5. **Báo người dùng** và chờ duyệt: tệp đã tạo, những gì đã bỏ. Người dùng (hoặc người duyệt) quyết định chuyển sang `pages/`. Agent không tự chuyển.
6. Ghi một dòng vào `log.md` của kho. Không sửa hay xóa trang nguồn trong dự án.

## Giới hạn

- Không đẩy trang nguồn nguyên văn lên kho chung rồi "sửa sau".
- Không commit hay push kho trừ khi người dùng yêu cầu.
- Còn ngờ một chi tiết thì bỏ chi tiết đó.
