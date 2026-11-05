AutoCAD MCP Launcher v0.2.11

# Tiếng Việt

Thay đổi chỉ nằm ở skill; không đổi mã launcher, gateway hay adapter.

Sửa bốn skill tri thức chung (`knowledge-query`, `knowledge-capture`, `knowledge-promote`, `knowledge-lint`) cho khớp với cơ chế sẵn có của launcher. Bản v0.2.10 giả định một thư mục kho riêng tên `common-knowledge`; điều đó không còn đúng.

- **Nguồn tri thức là `autocad-knowledge` công khai.** `knowledge-query` đọc thư mục `wiki/` mà nút **Tải tri thức** của launcher tải về (mặc định `~/autocad-knowledge`; đặt `COMMON_KNOWLEDGE_DIR` để dùng thư mục khác). Chưa tải thì đọc thẳng trên mạng, không cần đăng nhập.
- **Đối chiếu bản công khai trước khi ghi.** `knowledge-capture` và `knowledge-promote` đọc mục lục hiện hành trên GitHub, chỉ đề xuất phần còn thiếu, tránh tạo trang trùng.
- **Đề xuất nằm ở `proposals/`** trong thư mục tri thức, cạnh `wiki/`. Launcher chỉ ghi đè `wiki/` khi tải và không xóa gì, nên `proposals/` không bị mất.
- **`knowledge-lint` kèm sẵn script `scripts/lint.py`.** Kiểm tra đầu trang, liên kết gãy, trang chưa vào mục lục, trang quá một năm, và nội dung nhạy cảm (email, số điện thoại, đường dẫn máy, khóa, cùng danh sách thuật ngữ riêng ở `sensitive-terms.local.txt`). Trang công khai hiện có chưa có đầu trang nên chỉ bị cảnh báo.

Cần làm: tải lại lên Claude Desktop (Cài đặt, mục Skills) bốn file `knowledge-query.zip`, `knowledge-capture.zip`, `knowledge-promote.zip`, `knowledge-lint.zip`. Cần Python (`py -3`) để chạy lint.

Giới hạn đã biết:

- Vẫn chưa chạy bốn skill trong một phiên làm việc thật. Mới kiểm tra `lint.py` trên bản clone của `autocad-knowledge` (0 lỗi, 2 cảnh báo thiếu đầu trang) và trên một đề xuất cố ý sai (bắt đúng: reviewed_by, draft, liên kết gãy, thuật ngữ nhạy cảm, email).
- **Chưa có cổng tự động gửi đề xuất.** Người dùng phải gửi tệp trong `proposals/` cho người duyệt; người duyệt đưa trang vào repo công khai bằng tay. Cổng nhận đề xuất chưa làm.
- Lint chỉ biết thuật ngữ nhạy cảm bạn tự điền vào `sensitive-terms.local.txt`; không biết tên dự án mới.
- Tool tìm kiếm tri thức dạng MCP chưa có; skill đọc thư mục trên máy.
- Kế thừa từ v0.2.10: chưa lập thử một dự toán hoàn chỉnh bằng `tra-dinh-muc-du-toan`; `thiet-ke-phong-nha` chưa chạy trên mặt bằng thật; tab Revit pyRevit chưa thử với Revit đang mở; gateway (cổng 8764) không tự chạy sau khi Windows khởi động lại; bộ cài Windows chưa ký.

# English

The change is in skills only; no change to the launcher, gateway or adapter code.

The four shared-knowledge skills (`knowledge-query`, `knowledge-capture`, `knowledge-promote`, `knowledge-lint`) are reworked to match the launcher's existing mechanism. v0.2.10 assumed a separate store folder named `common-knowledge`; that is no longer the case.

- **The knowledge source is the public `autocad-knowledge` repo.** `knowledge-query` reads the `wiki/` folder that the launcher's **Download knowledge** button fetches (default `~/autocad-knowledge`; set `COMMON_KNOWLEDGE_DIR` to use another folder). If nothing is downloaded yet, it reads directly from the web, no login needed.
- **Check the public version before writing.** `knowledge-capture` and `knowledge-promote` read the current index on GitHub and propose only what is missing, to avoid duplicate pages.
- **Proposals live in `proposals/`** inside the knowledge folder, next to `wiki/`. The launcher only overwrites `wiki/` when downloading and deletes nothing, so `proposals/` is safe.
- **`knowledge-lint` now ships `scripts/lint.py`.** It checks front matter, broken links, pages missing from the index, pages over a year old, and sensitive content (emails, phone numbers, machine paths, keys, plus your own terms in `sensitive-terms.local.txt`). Existing public pages have no front matter yet, so they only get warnings.

To do: re-upload `knowledge-query.zip`, `knowledge-capture.zip`, `knowledge-promote.zip` and `knowledge-lint.zip` to Claude Desktop (Settings, Skills). Python (`py -3`) is needed to run lint.

Known limitations:

- The four skills still have not been run in a real working session. Only `lint.py` was tested, on a clone of `autocad-knowledge` (0 errors, 2 missing-front-matter warnings) and on a deliberately bad proposal (it caught the reviewer field, draft status, broken link, sensitive term and email).
- **There is no automatic gateway for submitting proposals yet.** Users must send the files in `proposals/` to the reviewer, who adds pages to the public repo by hand. The submission gateway is not built.
- Lint only knows the sensitive terms you put in `sensitive-terms.local.txt`; it cannot know a new project's name.
- There is no MCP knowledge-search tool yet; the skills read the folder on the machine.
- Carried over from v0.2.10: `tra-dinh-muc-du-toan` has not been used to build a complete estimate; `thiet-ke-phong-nha` has not been run on a real floor plan; the Revit pyRevit tab has not been tried against a running Revit; the gateway (port 8764) does not start by itself after Windows restarts; the Windows installer is unsigned.
