AutoCAD MCP Launcher v0.3.2

# Tiếng Việt

Sửa lỗi nghiêm trọng: mở launcher nhiều lần (hoặc mở ngay sau khi cập nhật) có thể tạo ra **nhiều cửa sổ launcher cùng lúc**.

Nguyên nhân: kiểm tra "đã có launcher đang chạy" chỉ tìm cửa sổ khay hệ thống, mà cửa sổ này chỉ có sau khi app khởi động xong. Hai lần mở sát nhau (bấm đúp hai lần, hoặc trình cập nhật mở lại launcher đúng lúc người dùng bấm) đều không thấy bản kia và cùng chạy.

Sửa:

- Launcher lấy một **khóa tiến trình (mutex) riêng cho mỗi thư mục cài** ngay từ đầu, trước mọi bước khởi động chậm. Lần mở thứ hai không tạo cửa sổ mới mà gọi cửa sổ đang chạy hiện lên (chờ tối đa 6 giây nếu bản kia còn đang khởi động) rồi tự thoát.
- Khóa tự giải phóng khi launcher thoát, kể cả khi bị tắt đột ngột; trình cập nhật chờ launcher cũ thoát rồi mới mở bản mới nên không bị chặn.

Cần làm:

- **Tắt hết các cửa sổ launcher đang mở** (Thoát hẳn từ biểu tượng khay, hoặc Task Manager nếu còn sót `pythonw.exe`), rồi mở lại một lần.
- Bản đang chạy cũ vẫn có lỗi này cho đến khi được thay bằng bản 0.3.2.

Đã kiểm chứng: 3 lần mở liên tiếp (kể cả một lần có `--start`) chỉ còn đúng một launcher sống; thêm test tự động cho khóa. Chưa thử bộ cài đóng gói và chưa thử trên máy thứ hai.

Giới hạn: hai thư mục cài khác nhau vẫn chạy song song được (cố ý, mỗi bản có khóa riêng). Các giới hạn khác giữ như v0.3.0.

# English

Critical fix: opening the launcher repeatedly (or right after an update) could create **several launcher windows at once**.

Cause: the "is a launcher already running" check only looked for the system-tray window, which exists only after the app has finished starting. Two launches close together (a double-click twice, or the updater relaunching just as the user clicks) each missed the other and both ran.

Fix:

- The launcher now takes a **per-install named process mutex** at the very start, before any slow startup work. A second start opens no window: it asks the running launcher to show itself (waiting up to 6 seconds if that one is still starting) and exits.
- The mutex is released when the launcher exits, even if killed; the updater waits for the old launcher to exit before starting the new one, so it is not blocked.

To do:

- **Close every open launcher window** (Quit from the tray icon, or Task Manager for any leftover `pythonw.exe`), then open it once.
- Running copies older than 0.3.2 keep the bug until replaced.

Verified: three starts in a row (one with `--start`) leave exactly one launcher alive; an automated test covers the mutex. The packaged installer and a second machine have not been tried.

Limitations: two different install folders can still run side by side (intended, each has its own mutex). Other limitations as in v0.3.0.
