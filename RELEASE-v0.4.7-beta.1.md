AutoCAD MCP Launcher v0.4.7-beta.1

> **Bản thử (pre-release).** Launcher của người dùng **không** tự cập nhật lên bản này. Tải bộ cài hoặc gói zip ở dưới để thử. Máy đã cài bản beta sẽ tự được đề nghị lên v0.4.7 chính thức khi bản đó phát hành.

# Tiếng Việt

Bản này đưa **CAD Studio (local)**, web chat gọi MCP ngay trên máy, vào sẵn trong bộ cài. Bản này cũng thêm MCP cho **LiteBIM và LiteCAD**.

Thêm:

- **CAD Studio (local) có sẵn trong launcher:** bộ cài kèm web đã build và `node.exe` riêng (thư mục `cadweb\`), nên **không cần cài Node.js hay chạy `npm install`**. Bấm **Mở CAD Studio (local)** ở tab Điều khiển, trình duyệt mở `http://localhost:8788`. Hội thoại và cấu hình lưu ở `launcher\state\cadweb\`, bản cập nhật không ghi đè thư mục này.
- **Cài và đăng nhập Claude CLI ngay trong CAD Studio:** khi máy chưa có Claude CLI, mục Cài đặt có nút **Tải và cài Claude CLI** (bộ cài chính thức của Anthropic, không cần quyền quản trị). Cài xong có nút **Đăng nhập Claude**, nút này mở cửa sổ đăng nhập. Trang tự cập nhật trạng thái.
- **MCP LiteBIM và LiteCAD (tùy chọn):** máy có LiteBIM thì gateway có thêm `http://127.0.0.1:8764/litebim/mcp` (12 tool). Máy có LiteCAD thì có thêm `/litecad/mcp`. **Tự thêm vào agent** cũng thêm hai mục này khi máy có. Chế độ kết nối ra server cũng gọi được hai đường này. Xem mục 2.11 trong `docs/HUONG-DAN-CAI-DAT-MAY-MOI.md`.

Đổi:

- Thư mục Beiming đổi tên từ `autocad-beiming-mcp-custom` thành `autocad-beiming-mcp`. Lần mở đầu tiên sau khi cập nhật, launcher tự chuyển `.venv` cũ sang thư mục mới và cài lại Beiming từ đó, không cần cài từ đầu.
- Cài MCP: nếu `.venv` mất `pip` thì tự khôi phục bằng `ensurepip` trước khi cài.

Cần làm:

- **Thoát hẳn launcher rồi mở lại.** Lần đầu có thể chậm thêm vài chục giây do bước chuyển `.venv` của Beiming.

Giới hạn:

- CAD Studio đóng gói: đã chạy thử bản build bằng `node.exe` riêng trên một máy (web, API, trạng thái Claude CLI). **Chưa thử** trên máy sạch không có Node.js, và chưa thử qua bộ cài `.exe`. Đó là mục đích của bản beta này.
- Bước chuyển `.venv` Beiming chỉ mới thử với một venv tạo để thử, **chưa thử** khi cập nhật thật từ v0.4.6.
- `litecad` chưa thử với LiteCAD thật. Với `litebim`, mới thử các lệnh đọc trên LiteBIM 27.4.19 thật. Chưa thử `run_script`/`edit_script`.
- Các giới hạn khác giữ như v0.4.6.

# English

This release ships **CAD Studio (local)**, the web chat that calls MCP on this machine, inside the installer. It also adds MCP for **LiteBIM and LiteCAD**.

Added:

- **CAD Studio (local) built into the launcher:** the installer carries the prebuilt web app and its own `node.exe` (folder `cadweb\`), so **no Node.js install and no `npm install`** are needed. Click **Mở CAD Studio (local)** on the Control tab and the browser opens `http://localhost:8788`. Conversations and settings live in `launcher\state\cadweb\`, which updates never overwrite.
- **Install and sign in to Claude CLI from CAD Studio:** when Claude CLI is missing, Settings shows **Tải và cài Claude CLI** (Anthropic's official installer, no admin rights). Once installed, **Đăng nhập Claude** opens the sign-in window. The page refreshes its status on its own.
- **LiteBIM and LiteCAD MCP (optional):** on a machine with LiteBIM the gateway also serves `http://127.0.0.1:8764/litebim/mcp` (12 tools). With LiteCAD it also serves `/litecad/mcp`. **Tự thêm vào agent** adds them when present, and outbound mode can call them too. See section 2.11 of `docs/HUONG-DAN-CAI-DAT-MAY-MOI.md`.

Changed:

- The Beiming folder is renamed from `autocad-beiming-mcp-custom` to `autocad-beiming-mcp`. On the first start after updating, the launcher moves the old `.venv` into the new folder and reinstalls Beiming from there, so there is no full reinstall.
- MCP install: if a `.venv` has lost `pip`, it is restored with `ensurepip` before installing.

To do:

- **Quit the launcher completely and reopen it.** The first start may take a few extra seconds while the Beiming `.venv` is moved.

Limitations:

- Packaged CAD Studio: the build was run with its own `node.exe` on one machine (web, API, Claude CLI status). **Not yet tried** on a clean machine without Node.js, or through the `.exe` installer. That is the purpose of this beta.
- The Beiming `.venv` move was tried only on a test venv, **not** on a real update from v0.4.6.
- `litecad` is not tried with real LiteCAD. For `litebim`, only read commands were tried, on real LiteBIM 27.4.19. `run_script`/`edit_script` are not tried.
- Other limitations as in v0.4.6.
