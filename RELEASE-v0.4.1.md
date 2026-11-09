AutoCAD MCP Launcher v0.4.1

# Tiếng Việt

Launcher tự tải và tự cập nhật dữ liệu dự toán `dutoan.db` từ cổng của nhóm, và khi cài skill thì ghi sẵn chỉ dẫn "việc AutoCAD thì nạp skill trước" vào tệp chỉ dẫn của agent.

Thêm:

- **Tự tải dữ liệu dự toán.** Khi mở launcher (và sáu giờ một lần) launcher hỏi cổng của nhóm, so SHA-256 với tệp trên máy và chỉ tải khi khác. Tệp tải về phải đúng SHA-256 và đủ bảng `don_gia`, `dinh_muc`, `tu_dien_vat_tu` mới thay bản cũ; lỗi thì giữ nguyên bản đang dùng. Tệp chép tay vẫn được nhận, không tải thừa.
- **Tab Cài đặt, mục Dữ liệu dự toán:** thêm ô **Khóa dữ liệu** (ẩn nội dung), nút **Cập nhật từ cổng nhóm** và ô tích bật hoặc tắt tự cập nhật. Cách tải theo địa chỉ cũ vẫn dùng được (nút **Tải theo địa chỉ**).
- **Cổng `knowledge-gateway`:** thêm `GET /dutoan/manifest` và `GET /dutoan/db` phát tệp từ kho R2 riêng tư; công cụ `tools/upload-dutoan.mjs` để tải dữ liệu lên. Hướng dẫn thiết lập ở README của `knowledge-gateway`.
- **Cài skill ghi chỉ dẫn cho agent:** khi bấm cài skill cho Claude Code hoặc Codex, launcher ghi một khối có đánh dấu vào `~/.claude/CLAUDE.md` hoặc `~/.codex/AGENTS.md`, để agent dùng skill AutoCAD cả khi launcher tắt. Khối được cập nhật tại chỗ, không đụng phần bạn tự viết. Claude Desktop không có tệp chỉ dẫn toàn cục nên không được ghi.

Cần làm:

- **Quản trị cổng (một lần):** bật R2, tạo bucket `dutoan-data`, đặt bí mật `DUTOAN_KEY`, triển khai lại cổng, rồi chạy `node tools/upload-dutoan.mjs <dutoan.db>`. Các bước ở README của `knowledge-gateway`.
- **Thành viên:** dán khóa dữ liệu do người quản lý cấp vào ô **Khóa dữ liệu**. Khóa này riêng, không nhúng sẵn trong launcher.
- Thoát hẳn launcher rồi mở lại sau khi cập nhật.

Lưu ý bảo mật:

- **Khóa nhóm chung nằm sẵn trong launcher công khai** (chỉ che mờ), nên không bảo vệ được dữ liệu dự toán. Hãy đặt `DUTOAN_KEY` riêng; nếu không, cổng dùng khóa nhóm chung và ai tải launcher cũng lấy được dữ liệu.

Giới hạn:

- Mới thử cổng ở máy cục bộ với kho R2 giả lập và tệp thử 2 MB: khóa chung bị từ chối (401), tải lần đầu đúng SHA-256, lần sau nhận ra đã mới nhất. **Chưa thử với Cloudflare thật, tệp 106 MB thật, hay bấm nút trong giao diện launcher**; chưa thử việc ghi chỉ dẫn khi cài skill trong giao diện.
- `dutoan.db` được chuyển từ phần mềm dự toán thương mại (GXD); chưa kiểm tra giấy phép cho phép chia sẻ trong nhóm. Tệp còn một tài khoản `admin` (mật khẩu băm) cần xóa trước khi tải lên cổng.
- Các giới hạn khác giữ như v0.4.0.

# English

The launcher now downloads and keeps the estimating data `dutoan.db` up to date from the team gateway, and installing skills also writes a "load the skill first for AutoCAD work" instruction into the agent's instruction file.

Added:

- **Automatic estimating data.** On start (and every six hours) the launcher asks the team gateway, compares the SHA-256 with the local file and downloads only when it differs. The download must match the SHA-256 and contain the tables `don_gia`, `dinh_muc`, `tu_dien_vat_tu` before it replaces the old file; on failure the current file is kept. A file copied by hand is recognised and not downloaded again.
- **Settings, "Dữ liệu dự toán":** a hidden **Khóa dữ liệu** field, a **Cập nhật từ cổng nhóm** button and a checkbox to turn automatic updates on or off. The address-based download still works (**Tải theo địa chỉ**).
- **`knowledge-gateway`:** adds `GET /dutoan/manifest` and `GET /dutoan/db`, serving the file from a private R2 bucket, plus `tools/upload-dutoan.mjs` to upload the data. Setup is in the `knowledge-gateway` README.
- **Skill install writes agent instructions:** installing skills for Claude Code or Codex writes a marked block into `~/.claude/CLAUDE.md` or `~/.codex/AGENTS.md`, so agents use the AutoCAD skills even when the launcher is off. The block is updated in place and never touches your own text. Claude Desktop has no global instruction file, so it is not written.

To do:

- **Gateway administrator (once):** enable R2, create the `dutoan-data` bucket, set the `DUTOAN_KEY` secret, redeploy the gateway, then run `node tools/upload-dutoan.mjs <dutoan.db>`. Steps are in the `knowledge-gateway` README.
- **Members:** paste the data key you were given into **Khóa dữ liệu**. This key is separate and is not embedded in the launcher.
- Quit the launcher completely and reopen it after updating.

Security note:

- **The shared team key ships inside the public launcher** (only obscured), so it cannot protect the estimating data. Set a separate `DUTOAN_KEY`; otherwise the gateway falls back to the shared key and anyone who downloads the launcher can fetch the data.

Limitations:

- The gateway was only tried locally with a simulated R2 bucket and a 2 MB test file: the shared key is refused (401), the first download matches the SHA-256, and the next run recognises it is current. **Not tried with real Cloudflare, the real 106 MB file, or by pressing the buttons in the launcher window**; the instruction block on skill install was not tried in the window either.
- `dutoan.db` was migrated from a commercial estimating package (GXD); whether the licence allows sharing within the team has not been checked. It also holds an `admin` account (hashed password) that should be removed before uploading to the gateway.
- Other limitations as in v0.4.0.
