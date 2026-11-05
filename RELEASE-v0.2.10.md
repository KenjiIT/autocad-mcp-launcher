AutoCAD MCP Launcher v0.2.10

# Tiếng Việt

Thay đổi chỉ nằm ở skill; không đổi mã launcher, gateway hay adapter.

Thêm bốn skill để quản lý kho tri thức chung (tri thức dùng chung giữa các dự án, không mật):

- `knowledge-query`: tra kho trước khi làm, đọc mục lục rồi chỉ mở trang liên quan; chỉ coi trang đã duyệt là đáng tin, nhắc rõ khi trang cũ hoặc chưa duyệt.
- `knowledge-capture`: ghi điều vừa học (cách đọc bản vẽ, lỗi công cụ, quy tắc) thành trang đề xuất, đã gỡ thông tin dự án, chờ người duyệt. Agent không tự ghi vào trang đã duyệt.
- `knowledge-promote`: chuyển trang tri thức riêng của một dự án thành bản chung; lập bảng "giữ / viết lại / bỏ" cho người dùng xem trước khi ghi.
- `knowledge-lint`: kiểm tra kho (đầu trang, liên kết gãy, trang quá hạn, thông tin nhạy cảm), rồi rà trùng lặp và mâu thuẫn.

Cần làm: tải lên Claude Desktop (Cài đặt, mục Skills) bốn file `knowledge-query.zip`, `knowledge-capture.zip`, `knowledge-promote.zip`, `knowledge-lint.zip`. Bốn skill này cần một thư mục kho tri thức riêng tên `common-knowledge` (đặt cạnh thư mục dự án hoặc trỏ bằng biến môi trường `COMMON_KNOWLEDGE_DIR`). Kho đó không nằm trong bản phát hành này; chưa có kho thì skill sẽ hỏi đường dẫn và không tự tạo.

Giới hạn đã biết:

- Chưa chạy bốn skill trong một phiên làm việc thật. Mới kiểm tra được script `lint.py` của kho (bắt đúng email, đường dẫn máy, thuật ngữ nhạy cảm, liên kết gãy, thiếu người duyệt, thiếu trong mục lục).
- Kho tri thức chung chưa có trang nào được duyệt; ba trang đầu tiên đang chờ duyệt.
- Danh sách thuật ngữ nhạy cảm (mã dự án, tên khách hàng) do từng người tự điền vào file cục bộ; lint không tự biết tên dự án mới.
- Kho chưa có nơi lưu trữ chung trên mạng, nên chưa chia sẻ được giữa các máy.
- Kế thừa từ v0.2.9: chưa lập thử một dự toán hoàn chỉnh bằng `tra-dinh-muc-du-toan`; `thiet-ke-phong-nha` chưa chạy trên mặt bằng thật; tab Revit pyRevit chưa thử với Revit đang mở; gateway (cổng 8764) không tự chạy sau khi Windows khởi động lại; bộ cài Windows chưa ký.

# English

The change is in skills only; no change to the launcher, gateway or adapter code.

Four new skills to manage a shared knowledge store (knowledge reused across projects, non-confidential):

- `knowledge-query`: look up the store before working; read the index and open only relevant pages; only approved pages are trusted, and old or unapproved pages are flagged.
- `knowledge-capture`: write what was just learned (how to read a drawing, tool pitfalls, rules) as a proposal page with project details removed, awaiting a reviewer. The agent never writes straight into approved pages.
- `knowledge-promote`: turn a project-private knowledge page into a shared version; shows a keep / rewrite / drop table to the user before writing.
- `knowledge-lint`: check the store (front matter, broken links, stale pages, sensitive information), then look for duplicates and contradictions.

To do: upload `knowledge-query.zip`, `knowledge-capture.zip`, `knowledge-promote.zip` and `knowledge-lint.zip` to Claude Desktop (Settings, Skills). These skills need a separate store folder named `common-knowledge` (next to the project folder, or pointed to by the `COMMON_KNOWLEDGE_DIR` environment variable). That store is not part of this release; without it the skills ask for the path and do not create one.

Known limitations:

- The four skills have not been run in a real working session. Only the store's `lint.py` script was tested (it caught emails, machine paths, sensitive terms, broken links, a missing reviewer and a missing index entry).
- The shared store has no approved pages yet; the first three are awaiting review.
- The sensitive-terms list (project codes, client names) is filled in by each person in a local file; lint cannot know a new project's name by itself.
- The store has no shared network location yet, so it cannot be shared between machines.
- Carried over from v0.2.9: `tra-dinh-muc-du-toan` has not been used to build a complete estimate; `thiet-ke-phong-nha` has not been run on a real floor plan; the Revit pyRevit tab has not been tried against a running Revit; the gateway (port 8764) does not start by itself after Windows restarts; the Windows installer is unsigned.
