# AutoCAD MCP Launcher v0.1.1

Bản cập nhật bổ sung bộ cài Windows dạng EXE.

## Có gì mới

- Bộ cài cho chọn thư mục cài đặt.
- Tự tạo shortcut trong Start Menu; có thể chọn thêm shortcut Desktop.
- Sau khi cài, có thể mở launcher để cài thư viện MCP lần đầu.
- Release có cả file cài EXE, gói ZIP đầy đủ và SHA-256 cho mỗi gói.

## Cài đặt

Tải `AutoCAD-MCP-Launcher-Setup-0.1.1.exe`, chạy bộ cài rồi làm theo hướng dẫn. Cần Windows 64-bit và Python 3.10–3.13 có `tkinter`; lần chạy đầu cần Internet để cài thư viện MCP.

Gói ZIP `autocad-mcp-launcher-complete.zip` vẫn có sẵn nếu muốn cài thủ công hoặc không muốn dùng bộ cài.

## Giới hạn đã biết

- AutoCAD cần chạy để thao tác DWG; xuất DXF offline dùng `ezdxf`.
- ChatGPT trên web cần endpoint HTTPS riêng để truy cập gateway trên máy.
- Hatch COM chưa được kiểm thử trên bản vẽ AutoCAD thực.
