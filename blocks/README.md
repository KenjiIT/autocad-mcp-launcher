# Thư viện block

Các file `.dwg` hoặc `.dxf` trong thư mục này là block dựng sẵn (nội thất, cây cối, thiết bị vệ sinh, cửa, ký hiệu bản vẽ). Công cụ `block` `insert` của MCP trên AutoCAD LT nạp chúng khi bản vẽ chưa có block cùng tên; `block` `list` liệt kê chúng kèm ý nghĩa, kích thước và đơn vị. Có thể đặt thư mục khác bằng biến môi trường `AUTOCAD_MCP_BLOCK_LIBRARY`. Quy trình cho agent nằm ở skill `autocad-block-library`.

## Nội dung có sẵn

Bộ khởi đầu gồm các block tách từ bản vẽ mẫu đi kèm AutoCAD LT (thư mục `Sample\en-us` trong nơi cài đặt). Đây là nội dung của Autodesk: các file `.dwg` này nằm ngoài git (`.gitignore`) và không được đóng gói kèm bản cài. Dựng lại trên máy có AutoCAD LT bằng `lt-adapter\tools\extract_sample_blocks.py`; cách chạy và danh sách block nằm trong skill `autocad-block-library`.

`index.json` ghi nguồn gốc và mô tả của từng file (block gốc, ý nghĩa, loại hình, đơn vị, kích thước, khung bao). `block list` đọc nó để trả thêm `meaning`, `view`, `size_mm`, `bbox_mm` và `scale_factor`.

## Quy ước tên

Tên file (bỏ đuôi) chính là tên block. Chỉ dùng chữ in hoa không dấu, số, dấu gạch ngang `-` và `_`, tối đa 80 ký tự. Không dùng dấu cách, dấu tiếng Việt, `/`, `\` hay `..`.

```
<NHÓM>-<LOẠI>[-<BIẾN THỂ>]-<RỘNG>x<SÂU>
```

| Nhóm | Dùng cho | Ví dụ |
|---|---|---|
| `FURN` | Nội thất | `FURN-BED-QUEEN-1525x2030`, `FURN-SOFA-7FT-2135x865` |
| `SANI` | Thiết bị vệ sinh | `SANI-WC-PLAN-535x840`, `SANI-SINK-OVAL-620x510` |
| `KITCH` | Thiết bị và tủ bếp | `KITCH-RANGE-PLAN-760x660`, `KITCH-SINK-DOUBLE-915x535` |
| `DOOR`, `WNDW` | Cửa đi, cửa sổ | `DOOR-LEFT-915x585`, `WNDW-WOOD-PLAN-915x150` |
| `PLANT` | Cây cối | `PLANT-TREE-DECIDUOUS-PLAN-3050x3050` |
| `SITE` | Ngoại thất | `SITE-POOL-10160x6230`, `SITE-CAR-SEDAN-SIDE-4420x1255` |
| `ARCH`, `CIVIL`, `ELEC` | Cấu kiện kiến trúc, hạ tầng, chiếu sáng | `ARCH-STAIR-SPIRAL-1525x1525`, `CIVIL-PARKING-STALL-2700x5500` |
| `SYMB`, `STRUC` | Ký hiệu bản vẽ, ký hiệu và tiết diện kết cấu | `SYMB-NORTH-ARROW-27x80`, `STRUC-WF-BEAM-105x105` |

- Hậu tố `<RỘNG>x<SÂU>` là kích thước thật tính bằng mm của hình chiếu bằng (hoặc của hình đang vẽ), khi block ở tỉ lệ 1 và góc xoay 0. Rộng theo trục X, sâu theo trục Y. Làm tròn 5 mm với vật thật, 1 mm với ký hiệu nhỏ.
- `<BIẾN THỂ>` là số chỗ ngồi, kiểu, hướng nhìn (`PLAN`, `ELEV`, `FRONT`, `SIDE`) hay số hiệu ngắn. Hai block khác nhau về hình thì phải khác tên.
- Tên không đổi sau khi đã dùng trong bản vẽ. Muốn sửa hình, tạo tên mới.

## Yêu cầu khi tự thêm file

1. **Khai báo đúng đơn vị chèn (`INSUNITS`).** Ưu tiên mm (`INSUNITS = 4`). File đơn vị khác vẫn dùng được nếu khai báo đúng: AutoCAD tự quy đổi khi chèn (file inch chèn vào bản vẽ mm được nhân 25,4). File khai báo sai đơn vị sẽ bị phóng sai (file mét chứa hình vẽ theo mm bị phóng 1000 lần). `block list` báo `scale_factor` để biết hệ số quy đổi; chỉ đọc được đơn vị của `.dxf` hoặc của file có trong `index.json`.
2. **Điểm chèn:** đặt ở vị trí có ý nghĩa với việc đặt block (tâm, hoặc mép sẽ áp vào tường). Ghi rõ trong `index.json` hoặc tên. Các block lấy từ bản vẽ mẫu giữ điểm chèn gốc nên không nằm ở tâm.
3. **Hình vẽ trên layer `0`, màu `ByLayer`** để block lấy layer và màu của bản vẽ chứa nó. Block mẫu của Autodesk chưa được kiểm điều này.
4. Chỉ có hình 2D, không có thuộc tính (`ATTDEF`) và không tham chiếu ngoài.
5. Một file một block, tên block bên trong trùng tên file.

## Cách dùng

```
block list                                  -> xem blocks (đã có trong bản vẽ) và library
block insert {name, x, y, scale, rotation}  -> chèn; scale để 1, kích thước thật nằm trong tên
```

Sau khi chèn, đọc lại `xscale` của đối tượng `INSERT`. Nó phải bằng `scale` nhân `scale_factor` của mục trong `library`. Khác thì file lệch đơn vị: xoá đối tượng vừa chèn và báo người dùng.
