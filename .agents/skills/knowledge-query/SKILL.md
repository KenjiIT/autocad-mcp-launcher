---
name: knowledge-query
description: Tra kho tri thức chung (quy tắc, cách đọc bản vẽ, lỗi hay gặp của công cụ CAD) trước khi bắt đầu một việc, chỉ nạp trang liên quan. Dùng khi bắt đầu việc mới về bản vẽ hoặc công cụ, khi gặp lỗi lạ, hoặc khi người dùng nói 'tra kiến thức chung', 'có ghi chú nào về', 'kinh nghiệm đọc bản vẽ', 'đã có ai gặp lỗi này chưa'.
---

# Tra kho tri thức chung

Kho tri thức chung là một thư mục git riêng (`common-knowledge`), chỉ chứa tri thức không mật. Quy ước nằm ở `CONVENTIONS.md` trong kho.

## Tìm kho

1. Biến môi trường `COMMON_KNOWLEDGE_DIR`, nếu có.
2. Thư mục `common-knowledge` nằm cạnh thư mục dự án hiện tại (`../common-knowledge`).
3. Không thấy thì hỏi người dùng đường dẫn một lần, rồi dùng đường dẫn đó cho cả phiên. Không tự tạo kho.

## Quy trình

1. Đọc `index.md` của kho: mỗi trang đã duyệt một dòng. Chọn trang khớp chủ đề.
2. Index không đủ thì tìm từ khóa trong `pages/` (tên layer, tên lỗi, thuật ngữ). Chỉ mở trang khớp, không nạp cả kho.
3. Đọc trang, đọc đầu trang (`status`, `updated`, `source`) trước nội dung.
4. Áp dụng vào việc đang làm và **nói rõ đã dựa vào trang nào** (`pages/<nhóm>/<tên>.md`).

## Mức tin cậy

- Chỉ coi `pages/` là đáng tin. `status: confirmed` dùng được.
- `status: outdated`: không dùng; xem trang thay thế nếu có.
- `updated` quá một năm: dùng nhưng nói với người dùng là trang cũ, cần kiểm lại.
- Trang trong `proposals/` là **chưa duyệt**. Chỉ dùng khi `pages/` không có gì, và nói thẳng "đây là đề xuất chưa được duyệt".
- Trang mâu thuẫn với bản vẽ hoặc yêu cầu của người dùng thì theo bản vẽ và người dùng, rồi báo mâu thuẫn để cập nhật (dùng `knowledge-capture`).

## Không tìm thấy

Nói là kho chưa có, làm tiếp theo cách thông thường. Nếu cuối việc rút ra được điều đáng ghi lại, đề nghị dùng `knowledge-capture`.

## Tri thức riêng của dự án

Kho này không chứa thông tin riêng của dự án (số liệu, quyết định, ràng buộc của khách). Các thông tin đó lấy từ nơi lưu riêng của dự án, không từ skill này.
