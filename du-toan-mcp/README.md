# Dự Toán MCP

MCP server cho phần mềm dự toán xây dựng. Agent (Claude, Codex, v.v.) có thể tra cứu đơn giá, lập dự toán, tính chi phí vận chuyển thông qua giao thức MCP.

## Kiến trúc

```
Agent (Claude Code / Claude Desktop / Codex)
  │
  │  MCP stdio
  ▼
dutoan-mcp (Python)
  │
  ▼
SQLite (data/dutoan.db)
```

## Cài đặt

```powershell
cd du-toan-mcp
pip install -e .
```

## Thiết lập dữ liệu

Cần file `data/dutoan.db` (~106 MB) chứa đơn giá, định mức, giá vật tư. Tệp này được chuyển từ phần mềm dự toán thương mại nên **không nằm trong git và không đi kèm bản phát hành công khai**.

### Cách 0: nhập từ tệp (đơn giản nhất)
Người quản lý gửi `dutoan.db` (hoặc zip chứa nó, nhỏ hơn nhiều). Trong launcher: tab **Cài đặt**, mục **Dữ liệu dự toán**, bấm **Nhập từ tệp…** và chọn tệp. Tệp được kiểm tra (kích thước, đủ bảng `don_gia`, `dinh_muc`, `tu_dien_vat_tu`) rồi mới thay bản cũ. Nếu báo tệp đang được dùng thì đóng các phiên agent đang mở công cụ dutoan rồi nhập lại.

### Cách 1: tải trong launcher (khi có địa chỉ tải riêng hoặc cổng nhóm)
Tab **Cài đặt**, mục **Dữ liệu dự toán**: dán địa chỉ https tải riêng do người quản lý cấp (SharePoint, Drive, kho riêng), điền SHA-256 nếu có, bấm **Tải dữ liệu dự toán**. Tệp được kiểm tra (kích thước, SHA-256, có đủ bảng `don_gia`, `dinh_muc`, `tu_dien_vat_tu`) rồi mới thay bản cũ.

### Cách 2: chép tay
Chép `dutoan.db` vào `data/` (hoặc đặt biến môi trường `DUTOAN_DB_PATH`).

### Cách 3: migration từ GXD (chỉ người quản lý dữ liệu)
```powershell
pip install pyodbc
set DUTOAN_MDB_DIR=<thư mục chứa các tệp MDB>

python scripts/migrate_mdb.py
```

## Khởi động

MCP server được kết nối tự động qua `.mcp.json` khi dùng Claude Code trong thư mục gốc.

Hoặc chạy thủ công:
```powershell
pip install -e .
dutoan-mcp
```

Launcher tự tạo môi trường `du-toan-mcp/.venv` và cấu hình agent dùng `python -m dutoan_mcp.server` trong đó. Server cần `mcp` bản 1.x (`mcp>=1.0.0,<2`); bản 2 đổi API nên server không khởi động.

## Cấu hình MCP cho client khác

### Claude Desktop
```json
{
  "mcpServers": {
    "dutoan": {
      "command": "python",
      "args": ["-m", "dutoan_mcp.server"],
      "env": {
        "PYTHONPATH": "đường/dẫn/tới/du-toan-mcp/src"
      }
    }
  }
}
```

## Danh sách tools

| Tool | Mô tả |
|------|-------|
| `search_don_gia` | Tra cứu đơn giá theo mã hoặc tên công việc |
| `phan_tich_don_gia` | Phân tích chi tiết VLC/NC/MTC cho một mã hiệu |
| `create_project` | Tạo dự án dự toán mới |
| `add_project_item` | Thêm công việc vào dự án |
| `get_project_summary` | Tổng hợp chi phí dự án (T/C/TL/G/GTGT/GXD) |
| `list_projects` | Liệt kê dự án đã tạo |
| `get_thvt` | Bảng tổng hợp vật tư - nhân công - máy |
| `search_vat_tu` | Tra cứu giá vật tư xây dựng |
| `calculate_cvc` | Tính chi phí vận chuyển vật liệu |
| `lookup_svdt` | Tra suất vốn đầu tư theo loại công trình |
| `calculate_svdt` | Tính ước tính chi phí từ suất vốn đầu tư |
| `compare_prices` | So sánh đơn giá giữa các tỉnh/thành phố |

## Công thức tính dự toán

```
Đơn giá = VLC + NC + MTC  (tra từ định mức × giá)

T   = VLC + NC + MTC + TT          (chi phí trực tiếp)
C   = T × chi phí chung %          (XD: 6.5%, LĐ: 5.5%)
TL  = (T + C) × thu nhập tính trước %  (5.5%)
G   = T + C + TL                   (trước thuế)
GTGT = G × VAT %                   (10%)
Nhà tạm = G × nhà tạm %           (1%)
GXD = G + GTGT + Nhà tạm           (tổng chi phí XD)
```

Tỷ lệ có thể chỉnh theo dự án qua ProjectSettings.
