AutoCAD MCP Launcher v0.4.7

# Tiếng Việt

Bản này đưa **CAD Studio (local)**, web chat gọi MCP ngay trên máy, vào sẵn trong bộ cài. Bản này cũng thêm MCP cho **LiteBIM và LiteCAD**.

Thêm:

- **CAD Studio (local) có sẵn trong launcher:** bộ cài kèm web đã build và `node.exe` riêng (thư mục `cadweb\`), nên **không cần cài Node.js hay chạy `npm install`**. Bấm **Mở CAD Studio (local)** ở tab Điều khiển, trình duyệt mở `http://localhost:8788`. Hội thoại và cấu hình lưu ở `launcher\state\cadweb\`, bản cập nhật không ghi đè thư mục này.
- **Cài và đăng nhập Claude CLI ngay trong CAD Studio:** khi máy chưa có Claude CLI, mục Cài đặt có nút **Tải và cài Claude CLI** (bộ cài chính thức của Anthropic, không cần quyền quản trị). Cài xong có nút **Đăng nhập Claude**, nút này mở cửa sổ đăng nhập. Trang tự cập nhật trạng thái.
- **CAD Studio có dự án và cột file:** mỗi dự án là một thư mục trên máy (mặc định `~\CAD Studio\projects`), có các cuộc trò chuyện riêng. Claude CLI và Codex làm việc ngay trong thư mục đó. Cột trái là cây dự án, cột phải là cây file của dự án: tạo, đổi tên, chép, di chuyển, kéo thả tải lên, tìm và mở file. Hộp chọn thư mục và file là hộp thoại thật của Windows. Có menu chuột phải.
- **CAD Studio: trang Cài đặt mới và thanh "Đã sử dụng":** Cài đặt có ô tìm và các nhóm mục. Đáy trang hiện hạn mức gói Claude (Pro/Max) và Codex (ChatGPT Plus/Pro), kèm thời gian còn lại tới lúc đặt lại. Số liệu đọc từ chính Claude CLI và nhật ký Codex.
- **MCP LiteBIM và LiteCAD (tùy chọn):** máy có LiteBIM thì gateway có thêm `http://127.0.0.1:8764/litebim/mcp` (12 tool). Máy có LiteCAD thì có thêm `/litecad/mcp`. **Tự thêm vào agent** cũng thêm hai mục này khi máy có. Chế độ kết nối ra server cũng gọi được hai đường này. Xem mục 2.11 trong `docs/HUONG-DAN-CAI-DAT-MAY-MOI.md`.
- **Skill điều phối dùng cho cả LiteCAD và LiteBIM:** `autocad-agent-coordinator` có thêm mục chọn ứng dụng (AutoCAD, LiteCAD hay LiteBIM) và quy trình dựng mô hình LiteBIM bằng script theo từng phần, kiểm tra bằng `view` sau mỗi lần chạy. MCP LiteBIM và LiteCAD có thêm tool `skills`, để agent nạp skill nghiệp vụ ngay từ ứng dụng đó.
- **Skill `thiet-ke-phong-nha`:** thêm quy tắc cánh cửa mở áp sát vách.

Đổi:

- Thư mục Beiming đổi tên từ `autocad-beiming-mcp-custom` thành `autocad-beiming-mcp`. Lần mở đầu tiên sau khi cập nhật, launcher tự chuyển `.venv` cũ sang thư mục mới và cài lại Beiming từ đó, không cần cài từ đầu.
- Cài MCP: nếu `.venv` mất `pip` thì tự khôi phục bằng `ensurepip` trước khi cài.

Cần làm:

- **Thoát hẳn launcher rồi mở lại.** Lần đầu có thể chậm thêm vài chục giây do bước chuyển `.venv` của Beiming.
- Dùng Claude Desktop: tải lại skill `autocad-agent-coordinator` và `thiet-ke-phong-nha` (bản zip trong `dist\`) ở Cài đặt, mục Skills.

Giới hạn:

- CAD Studio đóng gói: đã phát hành thử ở v0.4.7-beta.1 và chạy bản build trên máy làm (web, API dự án, hạn mức, trạng thái Claude CLI trả lời đúng). Phần dự án, cột file và hạn mức gói thêm sau bản beta. Chưa có kết quả thử trên máy sạch không có Node.js.
- Bước chuyển `.venv` Beiming mới thử với một venv tạo để thử, chưa có kết quả khi cập nhật thật từ v0.4.6.
- `litecad` chưa thử với LiteCAD thật. Với `litebim`, mới thử các lệnh đọc trên LiteBIM 27.4.19 thật. Chưa thử `run_script`/`edit_script`.
- Các giới hạn khác giữ như v0.4.6.

# English

This release ships **CAD Studio (local)**, the web chat that calls MCP on this machine, inside the installer. It also adds MCP for **LiteBIM and LiteCAD**.

Added:

- **CAD Studio (local) built into the launcher:** the installer carries the prebuilt web app and its own `node.exe` (folder `cadweb\`), so **no Node.js install and no `npm install`** are needed. Click **Mở CAD Studio (local)** on the Control tab and the browser opens `http://localhost:8788`. Conversations and settings live in `launcher\state\cadweb\`, which updates never overwrite.
- **Install and sign in to Claude CLI from CAD Studio:** when Claude CLI is missing, Settings shows **Tải và cài Claude CLI** (Anthropic's official installer, no admin rights). Once installed, **Đăng nhập Claude** opens the sign-in window. The page refreshes its status on its own.
- **CAD Studio projects and file column:** each project is a folder on this machine (default `~\CAD Studio\projects`) with its own conversations. Claude CLI and Codex work inside that folder. The left column is the project tree, the right column is the project's file tree: create, rename, copy, move, drag-and-drop upload, search and open files. Folder and file pickers are the real Windows dialogs. There is a right-click menu.
- **CAD Studio: new Settings page and usage bar:** Settings has a search box and grouped sections. The bottom of the page shows the Claude (Pro/Max) and Codex (ChatGPT Plus/Pro) plan limits with time until reset, read from Claude CLI itself and the Codex session logs.
- **LiteBIM and LiteCAD MCP (optional):** on a machine with LiteBIM the gateway also serves `http://127.0.0.1:8764/litebim/mcp` (12 tools). With LiteCAD it also serves `/litecad/mcp`. **Tự thêm vào agent** adds them when present, and outbound mode can call them too. See section 2.11 of `docs/HUONG-DAN-CAI-DAT-MAY-MOI.md`.
- **Coordinator skill covers LiteCAD and LiteBIM:** `autocad-agent-coordinator` gains a section on choosing the application (AutoCAD, LiteCAD or LiteBIM) and a LiteBIM workflow: build the model by script in parts and check with `view` after each run. The LiteBIM and LiteCAD MCPs gain a `skills` tool, so agents can load the domain skills from there.
- **`thiet-ke-phong-nha` skill:** adds a rule for door leaves opening flush against a wall.

Changed:

- The Beiming folder is renamed from `autocad-beiming-mcp-custom` to `autocad-beiming-mcp`. On the first start after updating, the launcher moves the old `.venv` into the new folder and reinstalls Beiming from there, so there is no full reinstall.
- MCP install: if a `.venv` has lost `pip`, it is restored with `ensurepip` before installing.

To do:

- **Quit the launcher completely and reopen it.** The first start may take a few extra seconds while the Beiming `.venv` is moved.
- On Claude Desktop: re-upload the `autocad-agent-coordinator` and `thiet-ke-phong-nha` skills (zips in `dist\`) under Settings, Skills.

Limitations:

- Packaged CAD Studio: shipped for testing as v0.4.7-beta.1 and the build was run on the dev machine (web, projects API, plan limits and Claude CLI status answer correctly). Projects, the file column and plan limits were added after the beta. No result yet from a clean machine without Node.js.
- The Beiming `.venv` move was tried only on a test venv; no result yet from a real update from v0.4.6.
- `litecad` is not tried with real LiteCAD. For `litebim`, only read commands were tried, on real LiteBIM 27.4.19. `run_script`/`edit_script` are not tried.
- Other limitations as in v0.4.6.
