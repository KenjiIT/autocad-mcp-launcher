# Kế hoạch bộ xác minh riêng cho AutoCAD LT (LISP/IPC, không dùng COM)

## Trạng thái thực hiện — 22/10/2026

- Đã thêm lệnh LISP chỉ-đọc `probe-snapshot`, `probe-entity`, `probe-vars`, `probe-area`, `probe-bbox`, `probe-hatch`, `probe-layer` và `probe-block`.
- Đã thêm thư viện `src/autocad_mcp/lt_verify.py` để gọi probe, so sánh snapshot theo handle, kiểm tra số đo có dung sai, chặn bản vẽ ngoài phạm vi thử và ghi báo cáo.
- Bộ xác minh hatch riêng cho LT đọc lại hatch và diện tích biên qua probe LISP/IPC; không gọi Python COM. Khi hậu kiểm sai, hatch thử được xóa qua IPC.
- Đã có runner thủ công `tests/manual_lt_verification.py`. Mặc định chỉ chạy với bản vẽ rỗng tên `Drawing*.dwg`; có thể cho phép thư mục thử qua `AUTOCAD_MCP_LT_TEST_ROOT`. Runner không lưu DWG.
- Chạy live trên AutoCAD LT 2027, `Drawing1.dwg`: hatch từ polyline và circle đều đạt; diện tích, layer, bounding box, entity DXF và biến hệ thống được đọc lại; handle hatch sai và batch delete chứa handle sai không làm đổi tập đối tượng. Cleanup đưa số đối tượng về 0.
- Báo cáo live gần nhất: `output/lt_verify/20261022-085320.md` và `.json`.
- Bộ test tập trung: 14 test đạt. Toàn bộ pytest có 5 lỗi liên quan các test COM/AutoCAD đầy đủ đang chạy trong môi trường chỉ có LT; 272 test đạt trước khi suite bị ngắt. Các lỗi này không nằm ở test probe mới.

Để tránh tranh chấp lệnh, runner độc lập yêu cầu dừng MCP Beiming ở cổng 8876 trước khi chạy. Gateway đã được khởi động lại sau lần kiểm tra live và hiện kết nối LT bình thường.

**Còn lại:** kiểm chứng đổi bản vẽ và đường dẫn Unicode; kiểm chứng `block.define`; chạy `copy_region_between_dwgs` trên hai DWG thử; thêm kịch bản live cho các tool LT còn lại và đo hiệu năng.

Ngày lập: 22/10/2026. Nhánh: `feature/custom-beiming-mcp`.

## Mục tiêu

Chứng minh từng tool LT làm đúng trên LT thật bằng dữ liệu đọc lại từ chính bản vẽ qua AutoLISP/IPC. Không dùng Python COM, không dựa vào lời tự báo "ok" của tool.

## Vì sao cần bộ riêng

- Nhiều bước xác minh hiện có dựa vào COM (`_collect_entities_via_com`, `_get_entity_via_com`, `drawing_audit`). Trên LT các hàm này lỗi.
- `_verify_entity_changes` ghi rõ "target geometry verification requires full AutoCAD COM", tức trên LT chỉ biết lệnh được chấp nhận chứ chưa biết hình học đúng.
- Backend LT đã chặn `_get_autocad_application()` nên không thể mượn đường COM.

## Nguyên tắc

1. **Quan sát độc lập với tool:** mỗi kiểm tra đọc trạng thái trước và sau bằng lệnh LISP chỉ-đọc riêng, không dùng chính giá trị trả về của tool đang kiểm.
2. **Chỉ dùng bản vẽ thử.** Mỗi lần chạy tự dựng bản vẽ thử bằng `entmake`, và xác nhận tên tài liệu là `Drawing*.dwg` hoặc nằm trong thư mục thử trước khi ghi. Từ chối chạy trên DWG khác.
3. **Mỗi kiểm tra có đối chứng:** trường hợp đúng, trường hợp sai đầu vào (kỳ vọng bị từ chối và bản vẽ không đổi), và rollback.
4. **Kết quả là số liệu so sánh được:** số lượng, handle, diện tích, toạ độ, layer, với dung sai nêu rõ.
5. **Tách bạch hai lớp lỗi:** lỗi hạ tầng (dispatcher, IPC, timeout, mã hoá) và lỗi nghiệp vụ (kết quả sai). Báo riêng.

## Thành phần

### 1. Lệnh quan sát chỉ-đọc trong `mcp_dispatch.lsp`
Thêm nhóm lệnh `probe-*`, không bao giờ ghi vào bản vẽ:

| Lệnh | Trả về |
|---|---|
| `probe-snapshot` | Số đối tượng theo loại và theo layer, `DBMOD`, tên tài liệu |
| `probe-entity` | `entget` đầy đủ theo handle: loại, layer, toạ độ, bán kính, pattern, mã nhóm |
| `probe-area` | Diện tích và chu vi của một đối tượng (`vlax-curve-getArea` hoặc `AREA`) |
| `probe-bbox` | Hộp bao của một tập handle |
| `probe-block` | Nội dung định nghĩa block (`tblsearch`, duyệt từng đối tượng đến `ENDBLK`) |
| `probe-hatch` | Pattern, scale, góc, số vòng biên, diện tích hatch |
| `probe-layer` | Thuộc tính layer: màu, loại đường, trạng thái |
| `probe-vars` | Giá trị biến hệ thống chỉ-đọc theo danh sách |

Lỗi dấu ngoặc là rủi ro lớn nhất của file này; giữ `tests/test_lisp_balance.py` chạy mỗi lần.

### 2. Thư viện Python `lt_verify`
- Gọi `probe-*` qua `_dispatch_unlocked` của backend LT, trả về dữ liệu cấu trúc.
- Hàm `snapshot()`, `diff(before, after)` cho biết đối tượng nào được thêm, xoá, đổi.
- Hàm khẳng định có thông báo rõ: kỳ vọng, thực tế, dung sai.

### 3. Bộ kịch bản kiểm chứng
Chạy từng bước: `snapshot` → thao tác → `snapshot` → `diff` → khẳng định.

| Nhóm | Kiểm tra |
|---|---|
| Hạ tầng | `ensure_ready`, `drawing.context`, nạp lại dispatcher sau khi đổi DWG, ký tự tiếng Việt trong đường dẫn, `TRUSTEDPATHS` |
| Hatch | Từ polyline kín và từ circle; diện tích hatch so với diện tích biên (dung sai); handle sai bị từ chối |
| `delete_batching` | Handle hợp lệ: đúng số đối tượng bị xoá và đúng handle; một handle sai: không xoá gì; `continue_on_error=true` bị từ chối |
| `block.define` | LINE, CIRCLE, ATTDEF: nội dung block khớp đầu vào; tên trùng bị từ chối |
| `copy_region_between_dwgs` | Preview: số đối tượng đúng; copy: DWG đích có đối tượng mới với hình học khớp; DWG nguồn không đổi; lỗi giữa chừng thì kiểm tra DWG đích |
| Tool mới ở `LT_TOOL_PLAN.md` | `layer_exists`, `entity_set_layer`, `entity_erase_layers`, `drawing_set_variables`, v.v., mỗi tool một kiểm tra theo cùng mẫu |

### 4. Báo cáo
- Mỗi lần chạy sinh bảng kết quả (đạt/không đạt/bị chặn), số liệu trước-sau, thời gian mỗi bước.
- Lưu vào `output/lt_verify/<ngày giờ>.md` và `.json`.
- Có đầu ra riêng cho các chỉ số trong "Nợ mở": tốc độ copy 5.000 đối tượng, thời gian nạp lại dispatcher.

## Thứ tự làm

| Bước | Nội dung | Thời gian |
|---|---|---|
| 1 | `probe-snapshot`, `probe-entity`, `probe-vars` và `lt_verify.snapshot/diff` | 2–3 giờ |
| 2 | Dựng bản vẽ thử bằng `entmake` và chốt chặn "chỉ chạy trên bản vẽ thử" | 1–2 giờ |
| 3 | Kịch bản hạ tầng và `delete_batching` | 1–2 giờ |
| 4 | `probe-area`, `probe-hatch` và kịch bản hatch | 2 giờ |
| 5 | `probe-block` và kịch bản `block.define` | 1–2 giờ |
| 6 | Kịch bản `copy_region_between_dwgs` (cần hai DWG thử) và đo tốc độ | 2–3 giờ |
| 7 | Báo cáo, và gắn các tool mới của `LT_TOOL_PLAN.md` | 2 giờ |

Tổng cộng khoảng 1–2 ngày làm việc.

## Chưa biết, phải xác minh trước

- `vlax-curve-*` và `vla-*` trong AutoLISP có chạy trên LT 2027 không. Chưa kiểm chứng; nếu không, dùng `entget`, `AREA` và tự tính.
- LT có chạy được hai bản vẽ cùng phiên qua IPC không (cần cho `copy_region_between_dwgs`).
- Chi phí nạp lại dispatcher mỗi lần gọi.

## Cần người dùng quyết định

1. Thư mục chứa DWG thử cố định, hay bộ xác minh tự dựng bản vẽ trống mỗi lần?
2. Có cần chạy tự động (không người trông) hay chỉ chạy tay khi có LT mở?
