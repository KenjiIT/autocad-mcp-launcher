# Dùng hai phiên AutoCAD MCP trong hai phiên Claude Code

Hướng dẫn này dành cho launcher thử nghiệm `launcher_multi`. Mỗi phiên MCP
được gắn với một PID AutoCAD riêng. Claude Code có thể thấy cả hai MCP, hoặc
mỗi cửa sổ Claude Code có thể được ghim vào đúng một MCP.

## 1. Mở hai MCP session

1. Chạy `launcher_multi\Start Multi-Session Launcher.cmd`.
2. Chọn PID AutoCAD thứ nhất rồi bấm **Mở MCP cho PID**.
3. Chọn PID AutoCAD thứ hai rồi bấm **Mở MCP cho PID**.
4. Chọn từng dòng và bấm **Test AutoCAD connection**. Chỉ giao việc cho phiên
   có trạng thái kết nối thành công.
5. Ghi lại PID và URL/cổng của từng dòng. Cổng được cấp lại khi khởi động, nên
   hãy kiểm tra launcher mỗi lần chạy lại.

MCP server chạy độc lập. Đóng cửa sổ Claude Code không dừng MCP; nút **Dừng
phiên MCP đã chọn** trong launcher mới dừng phiên server đó.

## 2. Cách đơn giản: một Claude thấy cả hai MCP

File `.mcp.json` ở thư mục dự án có thể chứa hai server. Khi Claude Code mở lại
dự án và được phép dùng project MCP, cả hai server sẽ hiện trong cùng phiên.
Agent cần chọn server có PID trùng với bản vẽ đang làm.

## 3. Ghim mỗi cửa sổ Claude vào một MCP

Tạo hai file JSON riêng. Mỗi file chỉ khai báo một server. Dùng URL đúng theo
cổng hiện trên launcher; ví dụ hiện tại:

`launcher_multi\runtime\claude-configs\claude-6280.json`

```json
{
  "mcpServers": {
    "autocad_beiming_6280": {
      "type": "http",
      "url": "http://127.0.0.1:8800/mcp"
    }
  }
}
```

`launcher_multi\runtime\claude-configs\claude-37692.json`

```json
{
  "mcpServers": {
    "autocad_beiming_37692": {
      "type": "http",
      "url": "http://127.0.0.1:8801/mcp"
    }
  }
}
```

Mở hai PowerShell terminal tại thư mục dự án. Chạy lệnh này ở terminal thứ
nhất:

```powershell
claude --strict-mcp-config --mcp-config ".\launcher_multi\runtime\claude-configs\claude-6280.json"
```

Chạy lệnh này ở terminal thứ hai:

```powershell
claude --strict-mcp-config --mcp-config ".\launcher_multi\runtime\claude-configs\claude-37692.json"
```

`--strict-mcp-config` làm phiên Claude chỉ nạp MCP trong file được chỉ định,
không lấy các MCP khác từ cấu hình dự án hoặc người dùng. Vì vậy mỗi terminal
chỉ thấy server được ghim cho nó. Nếu PID/cổng đổi, cập nhật URL và tên server
trong file tương ứng rồi mở lại phiên Claude.

## Kiểm tra trước khi giao việc

- Trong mỗi cửa sổ Claude, chạy `/mcp` và xác nhận chỉ có tên MCP mong muốn.
- Yêu cầu Claude gọi `system`/`ensure_ready` và xác nhận PID/active drawing khớp
  với cửa sổ AutoCAD đó.
- Ghi rõ trong prompt: “Chỉ dùng `autocad_beiming_<PID>` cho bản vẽ <tên file>.”
- Nếu kiểm tra kết nối timeout hoặc PID không khớp, dừng phiên đó và không gửi
  lệnh sửa bản vẽ.

Claude Code hỗ trợ HTTP MCP bằng `type: "http"` trong JSON và hỗ trợ
`--mcp-config` cùng `--strict-mcp-config` trên CLI. Tham khảo [MCP trong Claude
Code](https://docs.anthropic.com/en/docs/claude-code/mcp) và [CLI reference của
Claude Code](https://code.claude.com/docs/en/cli-usage).
