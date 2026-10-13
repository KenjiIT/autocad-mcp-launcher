# AutoCAD MCP Launcher

Ứng dụng Windows nối AutoCAD đang mở với hai MCP server, rồi tạo cấu hình để dùng trong Codex, Claude Code, Claude Desktop hoặc Cursor. Khi bật ứng dụng, `autocad_beiming` kết nối mặc định. Nếu agent gọi tool của `autocad_puran`, gateway ngắt MCP cũ trước khi kết nối MCP mới. Tại một thời điểm chỉ có một MCP làm việc với AutoCAD.

| MCP | Địa chỉ trong máy |
| --- | --- |
| [beiming183-cloud/AutoCAD-MCP](https://github.com/beiming183-cloud/AutoCAD-MCP) | `http://127.0.0.1:8764/beiming/mcp` |
| [puran-water/autocad-mcp](https://github.com/puran-water/autocad-mcp) | `http://127.0.0.1:8764/puran/mcp` |

Hai repo gốc được gắn dưới dạng Git submodule. Skill đi kèm hướng dẫn agent nói rõ phương án trước khi sửa bản vẽ và đọc lại kết quả sau khi dùng tool. Skill là hướng dẫn cho agent; MCP mới là thành phần thao tác với AutoCAD.

## 1. Tải về

Cần Windows, Python 3.10–3.13 có `tkinter`, AutoCAD đang mở với một bản vẽ, và Internet cho lần cài thư viện đầu tiên. Repo GitHub này là **private**, nên tài khoản GitHub tải về cần được cấp quyền.

### Máy không có Git

Mở [autocad-mcp-launcher-complete.zip](dist/autocad-mcp-launcher-complete.zip) trên GitHub, bấm **Download raw**, rồi giải nén. ZIP này chứa app, skill và mã nguồn của **cả hai MCP**. Mở thư mục `autocad-mcp-launcher` vừa giải nén và làm tiếp mục **2. Chạy app**. Máy dùng app không cần cài Git.

### Máy có Git

Mở PowerShell tại thư mục bạn muốn lưu app:

```powershell
git clone --recurse-submodules https://github.com/KenjiIT/autocad-mcp-launcher.git
cd autocad-mcp-launcher
```

Nếu đã clone mà hai thư mục MCP chưa có mã nguồn, chạy:

```powershell
git submodule update --init --recursive
```

**Không dùng nút Download ZIP của toàn bộ repo trên GitHub**: ZIP đó không chứa mã nguồn trong submodule. Hãy dùng tệp **complete.zip** ở trên hoặc lệnh clone kèm `--recurse-submodules`.

## 2. Chạy app

1. Mở AutoCAD và mở bản vẽ cần làm việc. Đóng các hộp thoại đang chặn AutoCAD.
2. Nhấp đúp `Start AutoCAD MCP.cmd` trong thư mục vừa clone hoặc giải nén.
3. Bấm **Bật kết nối cho agent** và đợi trạng thái `autocad_beiming` báo đã kết nối AutoCAD. Lần đầu app tạo môi trường Python riêng và cài thư viện cho từng MCP.
4. Giữ app chạy trong lúc dùng agent.

Bạn có thể xem trạng thái gateway tại `http://127.0.0.1:8764/status`. Nhật ký nằm trong `launcher/logs/`. App giữ AutoCAD mở khi đổi MCP hoặc tắt gateway.

## 3. Thêm MCP vào agent

Trong app, chọn agent ở ô **Agent**, bấm **Sao chép cấu hình**, rồi làm theo mục tương ứng dưới đây. Địa chỉ `127.0.0.1` chỉ dùng được trên chính máy đang chạy app.

### Codex

Gộp hai mục dưới đây vào `%USERPROFILE%\.codex\config.toml`, rồi mở lại Codex:

```toml
[mcp_servers.autocad_beiming]
url = "http://127.0.0.1:8764/beiming/mcp"

[mcp_servers.autocad_puran]
url = "http://127.0.0.1:8764/puran/mcp"
```

Skill của dự án đã nằm tại `.codex/skills/autocad-agent-coordinator/SKILL.md`. Mở Codex từ thư mục project này để nó có thể tìm skill. MCP và skill được cài riêng: phải có cả hai nếu muốn agent dùng CAD và làm theo quy trình điều phối.

### Claude Code

Mở terminal trong project này và chạy:

```powershell
claude mcp add --transport http autocad_beiming http://127.0.0.1:8764/beiming/mcp
claude mcp add --transport http autocad_puran http://127.0.0.1:8764/puran/mcp
```

Mở lại phiên Claude Code. Skill đã nằm tại `.claude/skills/autocad-agent-coordinator/SKILL.md`; có thể yêu cầu rõ: `/autocad-agent-coordinator` trước một việc CAD.

### Claude Desktop Chat

Mở hoặc tạo `%APPDATA%\Claude\claude_desktop_config.json`. Trong app chọn **Claude Desktop** và sao chép JSON được tạo theo đường dẫn trên **máy của bạn**. Gộp hai mục vào `mcpServers` hiện có, giữ nguyên các MCP khác. Thoát hẳn Claude Desktop, kể cả biểu tượng khay hệ thống, rồi mở lại. Trong Chat, bấm **+ → Connectors** để kiểm tra hai server và tool.

Để thêm skill vào Claude Chat: vào **Customize → Skills**, tải tệp `dist/autocad-agent-coordinator.zip` lên và bật skill. Việc tải skill không thay thế bước thêm MCP ở trên.

### Cursor

Gộp cấu hình này vào `%USERPROFILE%\.cursor\mcp.json`, rồi mở lại Cursor:

```json
{
  "mcpServers": {
    "autocad_beiming": { "url": "http://127.0.0.1:8764/beiming/mcp" },
    "autocad_puran": { "url": "http://127.0.0.1:8764/puran/mcp" }
  }
}
```

Skill trong repo hiện được đóng gói sẵn cho Codex, Claude Code và Claude Chat. Với Cursor, hãy đưa nội dung skill vào cơ chế hướng dẫn agent mà bạn đang dùng trong Cursor; chỉ thêm MCP sẽ không tự nạp skill.

### ChatGPT trên web

ChatGPT chạy trên cloud và không truy cập trực tiếp được `127.0.0.1` của máy bạn. Cần một endpoint HTTPS có xác thực và có thể truy cập từ Internet trước khi cấu hình MCP này trên ChatGPT web. App chưa tự tạo endpoint đó.

## 4. Dùng thử

Trong agent đã cấu hình, yêu cầu: “Kiểm tra bản vẽ AutoCAD đang mở, cho tôi biết tên bản vẽ và trạng thái kết nối. Chưa sửa gì.” Tool đọc trạng thái giúp xác nhận kết nối trước khi vẽ. Với yêu cầu thay đổi bản vẽ, skill sẽ hướng dẫn agent trình bày phương án bằng lời dễ hiểu trước khi gọi tool sửa, sau đó kiểm tra kết quả thực tế.

Nếu agent không hiện tool, kiểm tra theo thứ tự: app vẫn đang chạy; `/status` truy cập được; đã thêm cấu hình cho **đúng agent**; agent đã được khởi động lại; Claude Desktop đang ở **Chat**; và nhật ký trong `launcher/logs/` có lỗi hay không. Nếu `autocad_beiming` không kết nối, kiểm tra AutoCAD đang mở với một bản vẽ và không có hộp thoại chặn thao tác.

## Giới hạn và nguồn

Gateway dùng backend `file_ipc` để làm việc với AutoCAD. App tạm thêm thư mục LISP vào `TRUSTEDPATHS` khi tải dispatcher rồi khôi phục giá trị cũ; `SECURELOAD` không bị tắt. Skill hướng dẫn agent nhưng chưa phải một cơ chế bắt buộc ở gateway: agent có thể gọi thẳng MCP tool nếu không nạp hoặc không làm theo skill.

Mã nguồn hai MCP thuộc các repo upstream được dẫn ở đầu trang và giữ nguyên lịch sử Git của họ. Launcher và skill của dự án này nằm trong repo chính.

Người duy trì repo có thể tạo lại ZIP đầy đủ bằng `python scripts/build_portable.py` sau khi cập nhật launcher hoặc submodule. ZIP loại bỏ `.git`, môi trường `.venv`, log và file output phát sinh.
