AutoCAD MCP Launcher v0.4.2

# Tiếng Việt

Thêm cách đơn giản nhất để đưa dữ liệu dự toán vào máy: người quản lý gửi tệp `dutoan.db`, thành viên bấm **Nhập từ tệp** là xong.

Thêm:

- **Tab Cài đặt, mục Dữ liệu dự toán, nút "Nhập từ tệp…":** chọn tệp `dutoan.db` hoặc zip có chứa nó. Tệp được kiểm tra (kích thước, đủ bảng `don_gia`, `dinh_muc`, `tu_dien_vat_tu`) rồi mới thay bản cũ; lỗi thì giữ nguyên bản đang dùng. Zip có đúng một tệp `.db` và không được giải nén quá 2 GB.
- Gửi file nên nén zip: bản 109 MB nén còn khoảng 18 MB.
- Nếu công cụ dutoan đang chạy và giữ tệp, launcher báo rõ cần đóng phiên agent rồi nhập lại, thay vì báo lỗi hệ thống.

Giữ nguyên:

- Mã cổng nhóm và tự tải từ v0.4.1 vẫn còn, chỉ hoạt động khi có khóa dữ liệu; không dùng thì không ảnh hưởng. Cách tải theo địa chỉ cũng vẫn dùng được.

Cần làm:

- Người quản lý gửi bản **đã xóa tài khoản `admin`** (không gửi tệp đang dùng, vì vùng trống của SQLite còn giữ chuỗi băm). Cách tạo bản sạch: `VACUUM INTO` từ tệp đã xóa dòng `admin`.
- Thoát hẳn launcher rồi mở lại sau khi cập nhật.

Giới hạn:

- **`dutoan.db` được chuyển từ phần mềm dự toán thương mại (GXD)**; gửi tệp cho người khác vẫn là phát hành dữ liệu, chưa kiểm tra giấy phép có cho phép trong nhóm hay không.
- Đã thử nhập bản 109 MB và bản zip 18 MB thật vào thư mục tạm (SHA-256 khớp). Chưa bấm nút trong cửa sổ launcher, chưa cài thử bộ cài `.exe`.
- Các giới hạn khác giữ như v0.4.1.

# English

Adds the simplest way to get the estimating data onto a machine: the administrator sends the `dutoan.db` file and a member presses **Nhập từ tệp** (Import from file).

Added:

- **Settings, "Dữ liệu dự toán", button "Nhập từ tệp…":** pick a `dutoan.db` file or a zip containing it. The file is checked (size, required tables `don_gia`, `dinh_muc`, `tu_dien_vat_tu`) before it replaces the old one; on failure the current file is kept. The zip must hold exactly one `.db` file and may not expand beyond 2 GB.
- Zip the file before sending: the 109 MB file compresses to about 18 MB.
- If the dutoan tool is running and holding the file, the launcher says to close the agent sessions and import again, instead of showing a system error.

Unchanged:

- The team-gateway and automatic download code from v0.4.1 stays; it only runs when a data key is set, so leaving it unused changes nothing. Downloading from an address still works.

To do:

- The administrator sends a copy **with the `admin` account removed** (not the file in use, since SQLite's free space still holds the password hash). Make it with `VACUUM INTO` from the file after deleting the `admin` row.
- Quit the launcher completely and reopen it after updating.

Limitations:

- **`dutoan.db` was migrated from a commercial estimating package (GXD)**; sending the file to others is still distributing the data, and whether the licence allows that within the team has not been checked.
- Importing the real 109 MB file and the 18 MB zip was tried into a temporary folder (SHA-256 matched). Not tried by pressing the button in the launcher window, nor with the packaged installer.
- Other limitations as in v0.4.1.
