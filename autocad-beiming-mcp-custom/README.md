# AutoCAD Beiming MCP Custom

Bản MCP độc lập dựa trên AutoCAD-MCP của Beiming, có tích hợp thêm các tool thao tác theo lô. Thư mục này không chứa Git metadata của upstream; có thể khởi tạo remote riêng khi phát hành.

## Tool bổ sung

- `copy_batching`: sao chép nhiều đối tượng theo lô.
- `copy_region_between_dwgs`: chọn vùng chữ nhật/cắt qua và sao chép đối tượng giữa các bản vẽ.
- `delete_batching`: xóa nhiều đối tượng theo danh sách handle.
- `cad_batch`: gộp tối đa 100 thao tác entity vào một lần gọi MCP; hỗ trợ tham chiếu handle từ bước trước và rollback qua undo transaction khi có lỗi.

Các tool này được đăng ký trong server MCP nên client kết nối trực tiếp tới bản custom sẽ thấy chúng; không cần launcher đăng ký bổ sung.

## Chạy trên Windows

Cần Python 3.10 trở lên và AutoCAD nếu dùng backend AutoCAD. Tại thư mục này:

```powershell
py -3.12 -m pip install uv
uv sync
uv run autocad-beiming-mcp
```

MCP dùng stdio. Để cấu hình client, trỏ command đến `uv` và truyền `--directory` là đường dẫn tuyệt đối tới thư mục này, arguments là `run`, `autocad-beiming-mcp`.

Ví dụ Codex (`~/.codex/config.toml`):

```toml
[mcp_servers.autocad_beiming_custom]
command = "uv"
args = ["--directory", "C:/path/to/autocad-beiming-mcp-custom", "run", "autocad-beiming-mcp"]
```

Sau khi sửa cấu hình, khởi động lại MCP client để nạp danh sách tool.

## Nguồn và license

Đây là bản phái sinh từ AutoCAD-MCP của Beiming, phân phối theo MIT. Xem [LICENSE](LICENSE), [UPSTREAM_NOTES.md](UPSTREAM_NOTES.md) và [LOCAL_CHANGES.md](LOCAL_CHANGES.md) để biết nguồn, thay đổi cục bộ và ghi nhận tác giả.
