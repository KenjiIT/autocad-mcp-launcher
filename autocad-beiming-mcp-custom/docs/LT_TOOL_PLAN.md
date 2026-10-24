# Kế hoạch bổ sung tool 2D cho AutoCAD LT (nhánh LISP)

Ngày lập: 21/10/2026. Nhánh: `feature/custom-beiming-mcp`.

Cơ sở: quét tĩnh `src/autocad_mcp/backends/file_ipc.py` so với `lisp-code/mcp_dispatch.lsp`. Chưa chạy từng tool trên LT. Trên backend LT, `_get_autocad_application()` luôn báo lỗi, nên mọi tool phụ thuộc COM sẽ lỗi hoặc phải dùng nhánh LISP.

## Hiện trạng đã kiểm chứng trên LT 2027

- `system.ensure_ready` và `drawing.context` chạy được sau khi sửa hai lỗi: thiếu ngoặc trong `mcp_dispatch.lsp` và ký tự `\U+XXXX` trong JSON kết quả.
- Bốn tool LT (hatch, `delete_batching`, `block.define`, `copy_region_between_dwgs`) chưa kiểm chứng.
- `TRUSTEDPATHS` đọc được là rỗng tại thời điểm kiểm tra; cần xác nhận lại cấu hình.

## Danh mục tool

### COM có, LISP không có (trên LT sẽ lỗi)

| Nhóm | Tool |
|---|---|
| Bản vẽ và phiên | `drawing_activate`, `drawing_create`, `drawing_close`, `drawing_copy_dwg`, `drawing_save_as_dxf`, `drawing_set_variables`, `drawing_render_preview`, `recover`, `show_window` |
| Đối tượng và layer | `entity_set_layer`, `entity_erase_layers`, `entity_create_lines_file`, `entity_set_hatch_pattern`, `layer_exists` |
| Trình bày, quay hình | `apply_presentation_style`, `prepare_recording_view`, `product_render_view` |
| Solid 3D (ngoài phạm vi LT) | `solid_create_box`, `solid_create_cylinder`, `solid_extrude`, `solid_revolve`, `solid_sweep`, `solid_boolean`, `product_create_feature` |

### Có cả COM và LISP (cần kiểm từng tool)

`drawing_save`, `drawing_open`, `drawing_plot_pdf`, `drawing_audit` (có dự phòng `entity_list`), `entity_get`, `entity_trim`, `entity_extend`, `entity_join`, `layer_set_properties`, `create_dimension_linear`, `create_dimension_aligned`, `create_dimension_angular`, `create_dimension_radius`, `create_batch`, `zoom_extents`.

Chưa xác định tool nào tự rơi về LISP, tool nào lỗi hẳn trên LT.

### Đã có nhánh LISP riêng cho LT

`ensure_ready`, `document_context`, `status`, `create_hatch`, `delete_handles`, `block_define`, `region_operation`.

## Nguyên tắc chung

- Mỗi tool mới theo mẫu đã có: thêm lệnh `*-lt` trong `mcp_dispatch.lsp`, override trong `lt_file_ipc.py`; nhánh AutoCAD đầy đủ giữ nguyên COM.
- Tool ghi bản vẽ phải nhận `_expected_document_path` và dùng nhóm UNDO để rollback, như `delete_batching`.
- Mỗi giai đoạn kết thúc bằng một lần chạy thật trên DWG thử và một commit riêng.
- Không chạy thao tác ghi trên DWG công việc.

## Giai đoạn 0 — Lớp chặn lỗi (30 phút)

Trong `lt_file_ipc.py`, tool nào chưa có nhánh LT thì trả ngay lỗi rõ ràng (ví dụ `E_NOT_SUPPORTED_ON_LT`), không đi vào COM và không để agent bị timeout.

## Giai đoạn 1 — Chuẩn bị (30–45 phút, cần người dùng)

1. Người dùng mở một DWG thử riêng có sẵn line, circle, polyline kín, hatch; và một DWG thứ hai cho copy giữa hai bản vẽ.
2. Cài `pytest` vào `.venv` của `autocad-beiming-mcp-custom`.
3. Viết script probe gọi backend LT trực tiếp, chạy được từng tool một.
4. Thêm kiểm tra cân bằng dấu ngoặc cho `mcp_dispatch.lsp` vào bộ test (hai lỗi trước đều là thiếu `)`).

## Giai đoạn 2 — Tool đọc và layer (2–3 giờ, rủi ro thấp)

| Tool | Cách làm trong LISP |
|---|---|
| `layer_exists` | `tblsearch "LAYER"` |
| `drawing_set_variables` | `setvar` theo danh sách cho phép (`validate_variable_updates`), trả giá trị cũ để hoàn tác |
| `entity_set_layer` | `entmod` đổi mã nhóm 8; kiểm tra layer tồn tại trước |
| `entity_erase_layers` | `ssget "X"` lọc theo layer, `entdel`; từ chối layer `0` |

Kiểm chứng: đọc lại layer sau khi đổi; đếm đối tượng trước và sau.

## Giai đoạn 3 — Sửa đối tượng (2–3 giờ)

| Tool | Cách làm |
|---|---|
| `entity_set_hatch_pattern` | `entmod` đổi pattern; nếu LT không đổi được thì dựng lại hatch bằng `entmake` giữ biên cũ |
| `entity_create_lines_file` | Python đọc JSON rồi gửi lô LINE qua `entmake` (LISP không đọc JSON) |

Rủi ro: hatch trên LT chưa từng được xác nhận.

## Giai đoạn 4 — Xuất file và quản lý bản vẽ (3–4 giờ)

| Tool | Cách làm | Rủi ro |
|---|---|---|
| `drawing_save_as_dxf` | `command "_.SAVEAS" "DXF"` | Đổi tên bản vẽ hiện tại; phải khôi phục |
| `drawing_copy_dwg` | `_.WBLOCK` với tập chọn | Thay cho COM SelectionSets |
| `drawing_activate`, `drawing_create`, `drawing_close` | Điều khiển tài liệu từ LISP bị hạn chế trên LT | Có thể không làm được; khi đó trả lỗi rõ ràng |

## Giai đoạn 5 — Nhóm "có cả COM và LISP" (nửa ngày)

Chạy từng tool, ghi lại tool nào tự rơi về LISP và tool nào lỗi hẳn. Chỉ viết thêm LISP cho tool lỗi thật.

## Ngoài phạm vi

- Solid 3D (người dùng đã loại).
- `apply_presentation_style`, `prepare_recording_view`, `product_render_view`, `drawing_render_preview`, `show_window`: phụ thuộc đồ họa hoặc COM, giá trị thấp trên LT. Trả `E_NOT_SUPPORTED_ON_LT`.

## Thứ tự và thời gian

0 → 1 → 2 → 3 → 4 → 5. Khoảng 2–3 ngày làm việc.

## Cần người dùng quyết định

1. Đồng ý với phần "ngoài phạm vi" không, đặc biệt `drawing_create`, `drawing_close`, `drawing_activate`?
2. Khi nào có DWG thử cho giai đoạn 1? Không ghi lên bản vẽ khi chưa có.

## Trạng thái thực thi kế hoạch — 21/10/2026

| Giai đoạn | Trạng thái | Bằng chứng / phần còn lại |
|---|---|---|
| 0. Chặn tool chưa hỗ trợ | Hoàn tất | Tool chưa có nhánh LT trả `E_NOT_SUPPORTED_ON_LT` ngay. `entity_create_lines_file` đã được gỡ khỏi danh sách chặn sau khi có nhánh LISP. |
| 1. Chuẩn bị và kiểm thử | Phần offline hoàn tất | Đã tạo hai DWG thử riêng trong `%TEMP%\autocad-mcp-lt-smoke`, cài pytest vào `.venv`, thêm bài kiểm tra ngoặc LISP và unit test backend. 12 bài test đạt. Dispatcher nạp được trong AutoCAD LT Core Console. Kiểm thử cửa sổ LT trực tiếp chưa chạy được vì phiên LT thứ hai gặp Licensing Error khi bản vẽ công việc đang mở. |
| 2. Layer và biến | Đã triển khai | `layer_exists`, `drawing_set_variables`, `entity_set_layer`, `entity_erase_layers`; unit tests đạt. LISP `layer_exists`, cập nhật biến và tạo LINE chạy được trên DWG thử qua Core Console; thao tác GUI LT vẫn cần kiểm tra. |
| 3. Hatch và tạo LINE | Đã triển khai | `entity_set_hatch_pattern`, `entity_create_lines_file`; input được kiểm tra ở Python, cập nhật có UNDO trong LISP. Cần thử thêm trực tiếp trên phiên AutoCAD LT thật, nhất là đổi pattern hatch. |
| 4. Xuất file / quản lý document | Đã chặn rõ ràng, chưa triển khai | `drawing_save_as_dxf`, `drawing_copy_dwg`, `drawing_activate/create/close` trả `E_NOT_SUPPORTED_ON_LT`. Chưa làm DXFOUT/WBLOCK vì phải xác nhận chuỗi lệnh và trạng thái document trên LT để tránh đổi hoặc làm hỏng bản vẽ đang mở. |
| 5. Rà nhóm COM + LISP | Chưa hoàn tất kiểm thử runtime | Các nhánh LISP có sẵn tiếp tục được dùng qua backend; cần probe từng tool trên phiên LT thật và chỉ bổ sung nhánh cho các tool thực sự lỗi. |

Không ghi thay đổi lên DWG công việc. Lần kiểm tra Core Console cuối có một script probe bị treo do lỗi định dạng biểu thức LISP sau khi các kiểm tra layer, system variable và tạo LINE đã trả kết quả; tiến trình Core Console do lượt kiểm tra này tạo đã được dừng. Kết quả đó không thay thế bài kiểm thử end-to-end của MCP qua cửa sổ LT.

### Kết quả kiểm tra bổ sung

- Bộ test mục tiêu LT + biến: `12 passed`.
- Toàn bộ test suite: `266 passed`, `5 failed`, sau đó pytest bị ngắt. Ba lỗi chạm tới kiểm thử COM khi máy không có AutoCAD COM server khả dụng; một kiểm thử backend auto-detect thấy phiên LT thật đang mở nên kết quả khác kỳ vọng cũ; một kiểm thử dispatcher thất bại ở khâu lấy active document trước khi tới nhánh phân loại crash. Cần rà các lỗi nền này riêng, không xem chúng là pass của thay đổi LT.
- Core Console xác nhận dispatcher nạp được; probe cô lập xác nhận `layer_exists`, `drawing_set_variables`, và tạo 2 LINE chạy được trên DWG thử. Probe dài bị lỗi cú pháp ở phần biểu thức tiếp theo nên chưa tính `entity_set_layer`/`entity_erase_layers` là đã chạy thật.

### Probe lại ngày 21/10/2026

Trên các bản sao `LT_Verify3.dwg` và `LT_HatchProbe2.dwg`, Core Console AutoCAD LT 2027 trả kết quả thành công cho `layer_exists` (true), `drawing_set_variables` (INSUNITS 6 → 4), tạo 2 LINE, đổi layer cho 1 entity, xóa 1 entity theo layer và đổi pattern hatch thành `SOLID`. Tất cả chỉ ghi lên DWG thử trong `%TEMP%`.

`create_hatch` không chạy được trong Core Console: hàm VLA trả `VLA-OBJECT nil` vì phiên console không có ActiveDocument theo cách hàm đang lấy. Đây chưa xác định được hành vi trên LT GUI. Phiên LT GUI hiện vẫn là A-203 nên không chạy thử ghi trực tiếp vào đó.

### Probe bổ sung cho các tool LT

Trên bản sao `LT_OtherToolsProbe.dwg`, Core Console trả thành công cho `block.define` (tạo block thử với 2 entity), `copy_region_between_dwgs` preview (chọn 2 entity trong vùng), và `delete_batching` (xóa đúng 1 entity thử). Các phép thử chỉ dùng bản sao trong `%TEMP%`.

Tạo hatch vẫn cần kiểm tra trong AutoCAD LT GUI: lệnh dùng `vla-get-ActiveDocument`, và phép thử Core Console trả `VLA-OBJECT nil`. Phiên GUI đang mở A-203; giao diện điều khiển hiện không liệt kê cửa sổ native để chuyển sang bản sao DWG một cách an toàn.
