---
name: knowledge-query
description: Tra tri thức chung đã tải về máy (cách đọc bản vẽ Revit/DWG, quy tắc dầm, lỗi hay gặp khi dùng AutoCAD LT qua MCP) trước khi bắt đầu một việc, chỉ nạp trang liên quan. Dùng khi bắt đầu việc mới về bản vẽ hoặc công cụ, khi gặp lỗi lạ, hoặc khi người dùng nói 'tra kiến thức chung', 'có ghi chú nào về', 'kinh nghiệm đọc bản vẽ', 'đã có ai gặp lỗi này chưa'.
---

# Tra tri thức chung

Tri thức chung là **công khai, không mật**. Bản gốc là repo `KenjiIT/autocad-knowledge`; launcher tải thư mục `wiki/` về máy bằng nút **Tải tri thức** (tab Cài đặt). Quy ước đầy đủ: `references/quy-uoc.md` của skill `knowledge-capture`.

## Tìm thư mục tri thức

1. Biến môi trường `COMMON_KNOWLEDGE_DIR`, nếu có.
2. `~/autocad-knowledge` (mặc định của launcher; người dùng có thể đã đổi, tab Cài đặt của launcher hiện thư mục đang dùng).
3. Không thấy `wiki/` thì bảo người dùng bấm **Tải tri thức** trong launcher. Chưa tải được thì đọc thẳng trên mạng, không cần đăng nhập: `https://raw.githubusercontent.com/KenjiIT/autocad-knowledge/main/wiki/index.md`, rồi từng trang theo đường dẫn trong mục lục.

## Quy trình

1. Đọc `wiki/index.md`: mỗi trang một dòng. Chọn trang khớp chủ đề.
2. Mục lục chưa đủ thì tìm từ khóa trong `wiki/` (tên layer, mã lỗi, thuật ngữ). Chỉ mở trang khớp, không nạp cả thư mục.
3. Nếu trang có đầu trang, đọc `status`, `updated`, `source` trước nội dung.
4. Áp dụng vào việc đang làm và **nói rõ đã dựa vào trang nào** (`wiki/<nhóm>/<tên>.md`).

## Mức tin cậy

- Mọi trang trong `wiki/` đã được duyệt trước khi công khai. Dùng được, nhưng bản trên máy có thể cũ: nếu đã lâu chưa tải, nhắc người dùng bấm **Tải tri thức**.
- `status: outdated` (nếu có): không dùng; xem trang thay thế.
- `updated` quá một năm: dùng nhưng nói với người dùng là trang cũ, cần kiểm lại.
- Trang trong `proposals/` là **đề xuất chưa duyệt**. Chỉ dùng khi `wiki/` không có gì, và nói thẳng "đây là đề xuất chưa được duyệt".
- Trang mâu thuẫn với bản vẽ hoặc yêu cầu của người dùng thì theo bản vẽ và người dùng, rồi báo mâu thuẫn để cập nhật (dùng `knowledge-capture`).

## Không tìm thấy

Nói là tri thức chung chưa có, làm tiếp theo cách thông thường. Nếu cuối việc rút ra được điều đáng ghi lại, đề nghị dùng `knowledge-capture`.

## Tri thức riêng của dự án

Tri thức chung không chứa thông tin riêng của dự án (số liệu, quyết định, ràng buộc của khách). Các thông tin đó lấy từ nơi lưu riêng của dự án, không từ skill này.
