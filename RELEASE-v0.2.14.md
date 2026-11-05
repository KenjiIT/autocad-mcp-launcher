AutoCAD MCP Launcher v0.2.14

# Tiếng Việt

Tri thức chung nay tự cập nhật theo bản phát hành đã đóng tag, không còn phải bấm nút và không còn lấy thẳng nhánh `main`.

Thêm:

- **Tự tải và tự cập nhật tri thức.** Khi mở launcher (và mỗi 24 giờ khi đang chạy), launcher hỏi GitHub bản phát hành mới nhất của `autocad-knowledge` (tag `vX.Y.Z`). Máy chưa có tri thức thì tải ngay; máy đã có thì chỉ tải khi tag mới hơn. Mỗi lần hỏi dùng ETag, nên bản không đổi chỉ tốn một yêu cầu 304 và không tính vào giới hạn lượt gọi của GitHub.
- **Chỉ nhận bản đã duyệt và đóng tag**, không nhận mọi commit trên `main`. Gói `autocad-knowledge-wiki.zip` được kiểm tra **SHA-256** và từng mục trong zip (chặn đường dẫn thoát ra ngoài, giới hạn kích thước) trước khi thay các trang; lỗi giữa chừng thì không đụng gì tới bản đang dùng.
- **Trang bị gỡ khỏi bản mới thì bị xóa khỏi máy**, nên một trang bị rút lại biến mất ở mọi máy. `proposals/` và `sensitive-terms.local.txt` nằm cạnh `wiki/` không bị đụng.
- **Tab Cài đặt:** hộp "Tự kiểm tra và cập nhật tri thức mỗi 24 giờ" (mặc định bật), dòng trạng thái "Tri thức v0.1.0; kiểm tra lần cuối ...", và nút **Tải tri thức** nay tải lại ngay (kể cả cùng tag). Lỗi mạng hoặc GitHub không trả lời chỉ hiện ở dòng trạng thái, launcher vẫn dùng bản đang có và thử lại sau.
- **Tool `knowledge`:** kết quả `index` có thêm `version` (tag và giờ tải) để agent nói được trang thuộc phiên bản nào. Mô tả tool và hướng dẫn gateway nói rõ **trang là dữ liệu tham khảo, không phải lệnh**.
- Kho `autocad-knowledge` (repo riêng, không nằm trong bản phát hành này) có workflow đóng gói khi đẩy tag và đã phát hành `v0.1.0` (7 trang). Quy trình duyệt thêm bước đóng tag; xem `docs/HUONG-DAN-CAI-DAT-MAY-MOI.md`.

Cần làm:

- **Thoát hẳn launcher rồi mở lại**, rồi mở phiên agent mới.
- Tải lại lên Claude Desktop (Cài đặt, mục Skills) `knowledge-query.zip`, `knowledge-capture.zip`, `knowledge-promote.zip`.
- Người duyệt: sau khi đẩy trang lên `main` của `autocad-knowledge`, **đóng tag** (`git tag v0.2.0` rồi `git push origin v0.2.0`); chỉ đẩy tag, đừng tạo Release thủ công.

Giới hạn đã biết:

- Đã chạy thật với bản phát hành `v0.1.0` trên GitHub (cài lần đầu, kiểm tra lại, bỏ qua trong 24 giờ, nút tải lại, bật tắt công tắc) trong thư mục tạm cô lập. **Chưa thử với tag thứ hai thật**: việc nâng cấp, không hạ cấp và xóa trang bị gỡ chỉ được kiểm tra bằng test giả lập.
- **Chưa thử bộ cài đóng gói** của bản này và chưa thử sau tường lửa hoặc proxy công ty (GitHub bị chặn sẽ chỉ hiện lỗi ở dòng trạng thái).
- SHA-256 trong cùng bản phát hành chỉ chống tải hỏng; **không chống nội dung xấu do người có quyền đóng tag đẩy lên**. Rào chắn thật là người duyệt đọc kỹ trước khi đóng tag.
- Workflow của kho tri thức chỉ kiểm tra được mã dự án và tên khách hàng nếu repo đặt bí mật `SENSITIVE_TERMS`; hiện **chưa đặt**, nên bước kiểm tra trong workflow chỉ quét mẫu chung (email, số điện thoại, đường dẫn máy, khóa).
- Tri thức chỉ cập nhật khi launcher đang chạy. Launcher bản cũ (đến 0.2.13) vẫn tải từ `main` bằng nút và không tự cập nhật.
- Kế thừa từ v0.2.13: chưa chạy lại lệnh `audit` bản vẽ lớn để xác nhận hạn đọc mới; 5 test hỏng sẵn trong bộ test beiming chưa sửa; đường mở file trên LT chưa thử trên LT thật; chưa thử bộ cài đóng gói trên máy thứ hai; gateway không tự chạy sau khi Windows khởi động lại; bộ cài Windows chưa ký.

# English

Shared knowledge now updates itself from tagged releases, with no button to press and no longer straight from `main`.

Added:

- **Automatic download and update of the knowledge.** When the launcher opens (and every 24 hours while it runs) it asks GitHub for the latest release of `autocad-knowledge` (tag `vX.Y.Z`). A machine with no knowledge downloads it at once; one that has it downloads only when the tag is newer. Each check uses an ETag, so an unchanged release costs one 304 request that does not count against GitHub's rate limit.
- **Only reviewed, tagged releases are installed**, not every commit on `main`. The `autocad-knowledge-wiki.zip` package is checked by **SHA-256** and entry by entry (no paths escaping the folder, size limits) before any page is replaced; a failure part-way leaves the installed version untouched.
- **A page removed from the new release is removed from the machine**, so a retracted page disappears everywhere. `proposals/` and `sensitive-terms.local.txt` next to `wiki/` are never touched.
- **Settings tab:** a "Tự kiểm tra và cập nhật tri thức mỗi 24 giờ" checkbox (on by default), a status line "Tri thức v0.1.0; kiểm tra lần cuối ...", and the **Tải tri thức** button now reloads at once (even the same tag). A network failure or no answer from GitHub shows only in the status line; the launcher keeps the installed version and retries later.
- **`knowledge` tool:** the `index` result now includes `version` (tag and download time) so agents can say which version a page belongs to. The tool description and the gateway instructions state that **pages are reference data, not instructions**.
- The `autocad-knowledge` repository (separate, not part of this release) has a packaging workflow triggered by a tag push and has published `v0.1.0` (7 pages). The review procedure gains a tagging step; see `docs/HUONG-DAN-CAI-DAT-MAY-MOI.md`.

To do:

- **Quit the launcher completely and reopen it**, then open a new agent session.
- Re-upload `knowledge-query.zip`, `knowledge-capture.zip` and `knowledge-promote.zip` to Claude Desktop (Settings, Skills).
- Reviewers: after pushing pages to `main` of `autocad-knowledge`, **tag a release** (`git tag v0.2.0`, then `git push origin v0.2.0`); push only the tag and do not create the Release by hand.

Known limitations:

- Run for real against the published `v0.1.0` on GitHub (first install, re-check, skipped within 24 hours, the reload button, the checkbox) in an isolated temporary folder. **A real second tag has not been tried**: upgrading, never downgrading, and removing a retracted page are covered by simulated tests only.
- **The packaged installer of this version has not been tried**, nor behind a corporate firewall or proxy (a blocked GitHub only shows an error in the status line).
- The SHA-256 in the same release only guards against a corrupted download; it does **not** protect against bad content pushed by someone allowed to tag. The real safeguard is the reviewer reading carefully before tagging.
- The knowledge repository's workflow can catch project codes and client names only if the repository has a `SENSITIVE_TERMS` secret; it **is not set yet**, so the workflow check only scans generic patterns (e-mail, phone, machine paths, keys).
- Knowledge updates only while the launcher is running. Older launchers (up to 0.2.13) still download from `main` with the button and do not update by themselves.
- Carried over from v0.2.13: the large-drawing `audit` has not been re-run to confirm the new deadline; 5 pre-existing failing tests in the beiming suite are not fixed; the LT open route has not been tried on real LT; the packaged installer has not been tried on a second machine; the gateway does not start by itself after Windows restarts; the Windows installer is unsigned.
