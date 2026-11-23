AutoCAD MCP Launcher v0.4.9

# Tiếng Việt

Bản lớn cho **CAD Studio (local)** và **giao diện launcher**: nhiều phiên chạy song song, chọn agent khi tạo phiên (Claude CLI, Codex, Claude API) và cài/đăng nhập ngay trong app, chat lưu trong thư mục dự án, agent tự nạp skill và vẽ phương án mặt bằng thành hình, launcher có giao diện mới sáng/tối và hộp cập nhật mới.

Thêm (CAD Studio):

- **Chat lưu trong dự án:** mỗi dự án là một thư mục; hội thoại và ảnh lưu trong `<dự án>/.cadstudio/`. Mở lại thư mục là thấy lại các phiên cũ.
- **Khu Dự án:** nút **Dự án mới** và **Mở dự án có sẵn** (mở thư mục đã có `.cadstudio/` thì báo số phiên tìm thấy, không tạo trùng), kéo thả thư mục vào cột để mở. Hộp chọn thư mục/file kiểu mới của Windows (thanh địa chỉ, Quick access, ô tìm).
- **Xóa dự án kèm thư mục (tùy chọn):** tick "Xóa luôn thư mục dự án" rồi gõ OK; thư mục được chuyển vào **Thùng rác** (khôi phục được). Chặn xóa ổ gốc, thư mục tài khoản, Desktop/Documents/Downloads, thư mục chứa dự án khác, dự án đang chạy; báo rõ file đang bị chương trình khác mở.
- **Chọn agent khi tạo phiên:** Claude CLI, Codex CLI hoặc Claude API. Agent chưa cài/chưa đăng nhập/chưa có key thì bấm **Cài đặt / Đăng nhập / Nhập key** ngay trong menu, xong là tạo phiên luôn.
- **Cài đặt > Trợ lý AI:** danh sách agent kèm phiên bản, trạng thái và nút Cài / Đăng nhập / Cập nhật; chọn agent mặc định cho phiên mới. **Kiểm tra máy:** mạng tới claude.ai, Claude CLI, Git, PATH, Node/npm, đăng nhập, hồ sơ, có nút xử lý.
- **Cập nhật CLI:** báo khi Claude Code / Codex có bản mới và cập nhật bằng một nút (thanh dưới cùng).
- **Nhiều phiên song song:** tạo, mở và chuyển qua lại giữa các phiên khi phiên khác đang chạy; phiên cũ chạy ngầm, có chấm "đang chạy".
- **Phối hợp nhiều agent (giai đoạn 1):** bảng điều phối của dự án (dải "Đang làm", tab Trao đổi và Khoá), khoá file/bản vẽ giữa các agent.
- **Agent tự nạp skill:** mỗi lượt agent được báo các skill hiện có và phải nạp skill khớp việc trước khi làm. Skill thiết kế nhà có **lộ trình 6 bước**: hỏi thông tin lô đất, chọn hướng, **2-3 phương án mặt bằng vẽ thành hình SVG** đặt cạnh nhau, chọn, rồi mới dựng 3D, hoàn thiện. Chat hiện hình SVG agent vẽ (phóng to, tải về) và ảnh agent lưu trong thư mục dự án.
- **Gõ "/" ở bất kỳ đâu** trong câu để chọn skill; skill nhắc giữa câu vẫn được dùng.
- **Mức suy nghĩ** lưu theo từng phiên, phiên mới mặc định "Vừa".
- **Esc** dừng lượt đang chạy; tin vừa gửi về lại ô soạn để sửa. Nút **Sửa** trên tin cuối của bạn.
- **Tài liệu LiteBIM lưu sẵn:** launcher tự lưu tài liệu API LiteBIM/LiteCAD (theo phiên bản) để agent đọc thẳng, không phải gọi lại mỗi phiên.

Thêm (launcher):

- **Giao diện mới:** theme sáng/tối (theo Windows hoặc tự chọn trong Cài đặt), thanh tiêu đề theo theme, khối Dịch vụ có chấm màu, một nút Bật kết nối/Dừng, ô chọn agent hiện trạng thái MCP của từng agent.
- **Cài đặt theo nhóm:** Chung, Kết nối & dịch vụ, Agent & Skill, Dữ liệu, Cập nhật, Nâng cao; ô tìm nhanh (không cần dấu), nhớ nhóm mở lần cuối.
- **Cập nhật mới:** có bản mới thì hiện thẻ "Có bản mới" (không bật hộp chặn); hộp cập nhật có ghi chú phát hành, thanh tiến độ, Thử lại khi lỗi, **Bỏ qua bản này**, và chỉ khởi động lại khi bạn bấm "Khởi động lại để hoàn tất". Mục Cập nhật trong Cài đặt có nút Kiểm tra cập nhật.

Sửa:

- **Thêm vào agent cho Claude Code:** kiểm đúng tệp cấu hình mà lệnh `claude` ghi (kể cả khi đặt CLAUDE_CONFIG_DIR); báo rõ tệp và nguyên nhân khi lệch.
- **Cài và đăng nhập Claude CLI trên máy mới:** cửa sổ đăng nhập luôn hiện ra (kèm đường link nếu trình duyệt không mở), lỗi cài báo nguyên nhân (mạng/proxy, ExecutionPolicy) và tự thử cài qua npm; tìm `claude` ở `%USERPROFILE%\.local\bin` không cần PATH. Codex cũng mở cửa sổ đăng nhập theo cách mới.
- Agent Claude đọc được kết quả tool dài (tool-results) thay vì bảo người dùng cấp quyền thư mục.
- Câu hỏi của agent đã trả lời không còn hiện lại như chưa trả lời; ô tick ở chế độ tối thấy rõ; danh sách "Tệp đã nhắc tới" không trùng; nút "Mới nhất" ở góc phải không che hình.

Cần làm:

- Thoát hẳn launcher rồi mở lại. Trong CAD Studio, vào Cài đặt > Trợ lý AI bấm **Kiểm tra máy** một lần.
- Dùng Claude Code: bấm lại **Thêm vào agent** để thêm đủ 5 MCP (`autocad_puran`, `autocad_beiming`, `dutoan`, `litebim`, `litecad`).

Giới hạn:

- Phối hợp nhiều agent mới ở giai đoạn 1. Đăng nhập Claude/Codex vẫn cần bạn làm trên trình duyệt. Thông báo có bản mới chưa hiện ở khay hệ thống. Chuyển sang dự án khác khi một phiên đang chạy vẫn bị chặn.

# English

A large release for **CAD Studio (local)** and the **launcher UI**: parallel sessions, per-session agent choice (Claude CLI, Codex, Claude API) with in-app install and sign-in, chats stored in the project folder, agents load skills on their own and draw floor-plan options as images, and a new light/dark launcher with a new update flow.

Added (CAD Studio):

- **Chats stored in the project** (`<project>/.cadstudio/`); reopening a folder shows its sessions.
- **Projects area:** New project and Open existing project (no duplicates; reports sessions found), drag a folder in to open it, modern Windows folder/file picker.
- **Delete a project with its folder (optional):** moved to the Recycle Bin after typing OK; system folders, folders holding other projects, running projects are refused; locked files are named.
- **Pick the agent per session**, with Install / Sign in / Enter key right in the menu.
- **Settings > AI assistant:** agent list with version, status and actions; default agent for new sessions; **Machine check** with fix buttons.
- **CLI updates** for Claude Code and Codex from the status bar.
- **Parallel sessions:** create and switch sessions while another runs; it keeps running in the background.
- **Multi-agent coordination (phase 1):** project coordination board, messages and file/drawing locks.
- **Agents load matching skills** before working; the house-design skill follows a 6-step route with 2-3 SVG floor-plan options side by side before any 3D model. Chat renders agent SVGs and images saved in the project.
- **"/" anywhere** in the message to pick a skill; **effort** saved per session (default Medium); **Esc** stops the run and puts the message back; **Edit** on your last message.
- **LiteBIM reference cached** per version for agents to read directly.

Added (launcher):

- **New UI:** light/dark (follow Windows or choose), themed title bar, colored service status, single Start/Stop button, agent picker showing each agent's MCP status.
- **Settings by group** with quick search and remembered group.
- **New update flow:** non-blocking "New version" card, update dialog with notes, progress, retry, **Skip this version**, restart only when you choose.

Fixed:

- **Add to agent for Claude Code** now checks the file `claude` actually writes (including CLAUDE_CONFIG_DIR).
- **Claude CLI install and sign-in on a new machine:** the sign-in window always shows; install errors explain the cause and fall back to npm; `claude` found in `%USERPROFILE%\.local\bin` without PATH. Codex sign-in uses the same window.
- Claude reads long tool results; answered agent questions no longer reappear; dark-mode checkboxes visible; no duplicate "files mentioned"; the "Latest" button moved to the right.

To do:

- Quit the launcher completely and reopen it; run **Machine check** once in CAD Studio.
- Claude Code users: click **Add to agent** again to add all 5 MCPs.

Limitations:

- Multi-agent coordination is phase 1. Sign-in still needs the browser. No tray notification for new versions yet. Switching projects while a session runs is still blocked.
