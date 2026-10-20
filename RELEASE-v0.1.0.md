# AutoCAD MCP Launcher v0.1.0

Bản phát hành đầu tiên của launcher độc lập cho AutoCAD MCP.

## Có gì mới

- Chạy Beiming custom MCP và Puran MCP từ một ứng dụng Windows, có gateway dùng chung cho agent.
- Tự kiểm tra GitHub Releases khi mở ứng dụng; cho người dùng chọn tải và cài bản mới. Gói tải về được xác minh bằng SHA-256.
- Tạo hatch qua COM bằng polyline biên được chỉ định, rồi kiểm tra diện tích hatch.
- Hỗ trợ các thao tác sao chép theo lô, sao chép đối tượng trong vùng giữa hai DWG và xóa theo lô.
- Phát hành gói `autocad-mcp-launcher-complete.zip`, không yêu cầu Git trên máy người dùng.

## Cài đặt

Tải `autocad-mcp-launcher-complete.zip` từ phần Assets bên dưới, giải nén rồi chạy `Start AutoCAD MCP.vbs`. Cần Windows và Python 3.10–3.13; lần đầu chạy cần Internet để cài các thư viện.

Máy đang dùng bản cũ cần tải và giải nén gói này thủ công một lần. Các bản sau có thể cập nhật từ thông báo trong launcher.

## Giới hạn đã biết

- Vẽ DWG cần AutoCAD đang chạy; xuất DXF offline dùng `ezdxf`.
- ChatGPT trên web không truy cập trực tiếp gateway `127.0.0.1`; cần endpoint HTTPS riêng.
- Luồng hatch COM đã được biên dịch và đóng gói; chưa kiểm thử thao tác hatch trên bản vẽ AutoCAD thực trong lần phát hành này.
