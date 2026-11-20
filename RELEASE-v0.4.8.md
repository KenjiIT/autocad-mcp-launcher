AutoCAD MCP Launcher v0.4.8

# Tiếng Việt

Bản này cải thiện **CAD Studio (local)**: báo khi agent làm xong, xem ảnh ngay trong trang, kéo đổi bề rộng cột, và tùy chọn cho agent chạy lệnh trong thư mục dự án.

Thêm:

- **Thông báo khi agent xong hoặc cần bạn trả lời:** chỉ hiện khi bạn không đang nhìn trang CAD Studio. Mở trang ngay trên máy này thì popup hiện ở góc dưới phải màn hình (không bị Focus assist nuốt mất), tự tắt sau 15 giây, rê chuột lên thì giữ lại. Mở từ máy khác thì dùng thông báo của trình duyệt. Bật hoặc tắt trong Cài đặt, có nút gửi thử.
- **Xem ảnh trong trang:** bấm ảnh để mở cửa sổ nổi. Lăn chuột để phóng to hoặc thu nhỏ, kéo để di chuyển, bấm đúp để về vừa khung, Esc để đóng.
- **Kéo đổi bề rộng cột** dự án và cột file. Bấm đúp vào thanh kéo để về mặc định. Bề rộng được giữ khi tải lại trang.
- **Cho agent chạy lệnh (tùy chọn, theo từng dự án):** bật trong Cài đặt dự án thì Claude CLI được chạy lệnh (Bash) trong thư mục dự án. Mặc định tắt: agent chỉ đọc và sửa file.

Sửa:

- Gửi lỗi thì tin đã gõ (kèm ảnh) được giữ lại để gửi lại, không phải gõ lại từ đầu.
- Phiên chat mới hiện ngay trong danh sách. Đang ở một phiên trống thì không tạo thêm phiên trống.
- Biểu tượng file có màu nhạt theo loại file.

Cần làm:

- Thoát hẳn launcher rồi mở lại.

Giới hạn:

- Popup thông báo và quyền chạy lệnh mới thử trên máy làm, chưa thử trên máy sạch. Các giới hạn khác giữ như v0.4.7.

# English

This release improves **CAD Studio (local)**: notifications when the agent finishes, in-page image viewer, resizable columns, and an option to let the agent run commands in the project folder.

Added:

- **Notification when the agent finishes or needs your answer:** shown only when you are not looking at the CAD Studio page. When the page is open on this machine, a popup appears at the bottom-right of the screen (not swallowed by Focus assist), closes after 15 seconds, and stays while hovered. From another machine the browser's notification is used. Toggle it in Settings, with a test button.
- **In-page image viewer:** click an image to open it. Scroll to zoom, drag to pan, double-click to fit, Esc to close.
- **Resizable project and file columns.** Double-click the handle to reset. Widths survive a reload.
- **Let the agent run commands (optional, per project):** when enabled in project settings, Claude CLI may run commands (Bash) in the project folder. Off by default: the agent only reads and edits files.

Fixed:

- If sending fails, the typed message (with images) is kept so it can be sent again.
- A new chat session appears in the list right away. An empty session is reused instead of creating another.
- File icons get a soft color by file type.

To do:

- Quit the launcher completely and reopen it.

Limitations:

- The notification popup and command permission were tried only on the dev machine, not on a clean machine. Other limitations as in v0.4.7.
