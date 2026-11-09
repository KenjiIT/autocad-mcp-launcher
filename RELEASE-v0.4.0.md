AutoCAD MCP Launcher v0.4.0

# Tiếng Việt

Thêm công cụ **dutoan** (tra đơn giá, định mức, lập dự toán) vào launcher. Dữ liệu `dutoan.db` **không đi kèm** và không được đưa lên chỗ công khai; mỗi máy tải riêng từ địa chỉ do người quản lý cấp.

Thêm:

- **MCP `dutoan` (12 tool):** `search_don_gia`, `phan_tich_don_gia`, `create_project`, `add_project_item`, `get_project_summary`, `search_vat_tu`, `calculate_cvc`, `lookup_svdt`, `calculate_svdt`, `compare_prices`, `get_thvt`, `list_projects`. Chạy kiểu stdio trong môi trường riêng `du-toan-mcp/.venv`, được launcher cài ở lần chạy đầu và đồng bộ khi cập nhật.
- **Cấu hình cho agent:** mục "Cấu hình agent" nay có sẵn dòng `dutoan` cho Claude Code, Codex và Claude Desktop, trỏ thẳng tới Python trong môi trường riêng.
- **Tab Cài đặt, mục Dữ liệu dự toán:** dán địa chỉ https và SHA-256 (nên điền), bấm **Tải dữ liệu dự toán**. Tệp được kiểm tra (kích thước, SHA-256, có đủ bảng `don_gia`, `dinh_muc`, `tu_dien_vat_tu`) rồi mới thay bản cũ; lỗi thì giữ nguyên bản đang dùng. Có nút mở thư mục dữ liệu để chép tay.
- Trang chủ launcher hiện trạng thái `dutoan` (sẵn sàng hoặc chưa có dữ liệu).

Sửa:

- Server `dutoan` trước đây **không khởi động** (báo "Connection closed") vì thư viện `mcp` bản 2 đổi API; nay ghim `mcp>=1.0.0,<2`, và cấu hình không còn gọi `python` hay `dutoan-mcp` chưa cài.
- Bỏ đường dẫn cá nhân trong mã (`DUTOAN_MDB_DIR` đọc từ biến môi trường).
- Bản phát hành không chứa `dutoan.db`, môi trường ảo hay thư mục `data`.

Cần làm:

- **Thoát hẳn launcher rồi mở lại.** Lần mở đầu sẽ cài môi trường `dutoan` (thêm vài phút, cần mạng).
- Người quản lý: đặt `dutoan.db` ở một địa chỉ **riêng tư** có link tải trực tiếp và đưa link cùng SHA-256 cho thành viên.

Giới hạn:

- **`dutoan.db` được chuyển từ phần mềm dự toán thương mại (GXD)**; chưa kiểm tra giấy phép cho phép chia sẻ trong nhóm hay không. Đừng đưa lên kho công khai. Tệp còn chứa một tài khoản `admin` (mật khẩu băm) của bản web cũ; MCP không dùng nhưng nên xóa trước khi chia sẻ.
- Link SharePoint thường là trang đăng nhập, không phải tải trực tiếp; launcher chỉ tải được link trực tiếp (không cần đăng nhập). Chưa thử với link thật.
- Chưa thử bộ cài đóng gói và việc cài môi trường `dutoan` trên máy thứ hai. Tool `dutoan` mới thử ở mức liệt kê tool và một lệnh tra; chưa thử đủ 12 tool. Chưa đối chiếu độ chính xác của kết quả với phần mềm gốc.
- Các giới hạn khác giữ như v0.3.5.

# English

Adds the **dutoan** tool (unit prices, norms, cost estimates) to the launcher. The `dutoan.db` data is **not bundled** and is never put anywhere public; each machine downloads it from an address the administrator provides.

Added:

- **`dutoan` MCP (12 tools):** `search_don_gia`, `phan_tich_don_gia`, `create_project`, `add_project_item`, `get_project_summary`, `search_vat_tu`, `calculate_cvc`, `lookup_svdt`, `calculate_svdt`, `compare_prices`, `get_thvt`, `list_projects`. Runs over stdio in its own `du-toan-mcp/.venv`, installed by the launcher on first run and refreshed on update.
- **Agent configuration:** the "Cấu hình agent" snippets now include `dutoan` for Claude Code, Codex and Claude Desktop, pointing at the Python in that environment.
- **Settings, "Dữ liệu dự toán":** paste an https address and SHA-256 (recommended), press **Tải dữ liệu dự toán**. The file is checked (size, SHA-256, required tables `don_gia`, `dinh_muc`, `tu_dien_vat_tu`) before replacing the old one; on failure the current file is kept. A button opens the data folder for manual copying.
- The launcher's main tab shows the `dutoan` status (ready or no data).

Fixed:

- The `dutoan` server **did not start** ("Connection closed") because `mcp` version 2 changed its API; it now pins `mcp>=1.0.0,<2`, and the configuration no longer calls a bare `python` or an uninstalled `dutoan-mcp`.
- Removed a personal path from the code (`DUTOAN_MDB_DIR` now comes from the environment).
- The release contains no `dutoan.db`, virtual environment or `data` folder.

To do:

- **Quit the launcher completely and reopen it.** The first start installs the `dutoan` environment (a few more minutes, network needed).
- Administrator: host `dutoan.db` at a **private** address with a direct download link and give members the link and SHA-256.

Limitations:

- **`dutoan.db` was migrated from a commercial estimating package (GXD)**; whether its licence allows sharing within the team has not been checked. Do not put it in a public repository. It also holds an `admin` account (hashed password) from the old web app; the MCP does not use it, but remove it before sharing.
- A SharePoint link is usually a sign-in page, not a direct download; the launcher can only fetch direct links (no sign-in). Not tried with a real link.
- The packaged installer and the `dutoan` environment install on a second machine have not been tried. The `dutoan` tools were only tried at the level of listing tools and one lookup, not all 12, and results have not been checked against the original package.
- Other limitations as in v0.3.5.
