# Kế hoạch hoàn thiện adapter AutoCAD LT (các việc còn lại sau khi tách adapter)

Ngày lập: 22/10/2026. Repo: `C:\Users\minhk\orca\projects\MCP Deploy`. Nhánh: `feature/custom-beiming-mcp`.
Đọc cùng: `docs/LT_ADAPTER_PLAN.md`, `lt-adapter/README.md`, `autocad-beiming-mcp-custom/docs/LT_TOOL_PLAN.md`, `autocad-beiming-mcp-custom/docs/LT_VERIFY_PLAN.md`.

## 1. Bối cảnh và những gì đã kiểm chứng

Phần LT đã tách khỏi mã upstream Beiming vào `lt-adapter/` (`bootstrap.py` hook chọn backend, `lt_file_ipc.py` backend, `lisp/mcp_dispatch_lt.lsp` lớp LISP phủ lên dispatcher upstream, `custom_tools/` hai tool thay thế). `launcher/serve.py` cài adapter trước khi import `autocad_mcp.server`.

Kiểm chứng ngày 22/10/2026 trên AutoCAD LT 2027 thật, chạy qua `launcher/serve.py`, bản vẽ thử:
- `system.ensure_ready`, `system.get_backend`: backend `file_ipc_lt`, sản phẩm "AutoCAD LT".
- `drawing.create` (tool chỉ có COM): trả `E_NOT_SUPPORTED_ON_LT`.
- Hatch trên circle bán kính 10: diện tích 314.159, khớp π×10².
- `block.define` LINE/CIRCLE/ATTDEF: tạo 3 đối tượng; tên trùng bị từ chối.
- `delete_batching`: `continue_on_error=true` bị từ chối; handle sai định dạng bị từ chối; lô có handle không tồn tại thì không xóa gì; xóa handle hợp lệ đúng số lượng.
- `copy_region_between_dwgs`: preview chọn đúng 2 đối tượng; copy với offset (100,0) ra đúng LINE (110,10)-(140,10) và CIRCLE tâm (120,20) r=5 ở bản đích; bản nguồn không đổi. Đã đọc lại bằng LISP độc lập, không dựa vào lời tự báo của tool.
- Test: 17 test LT mới đạt. Toàn bộ bộ test: 307 đạt, 6 lỗi; 6 lỗi này cũng xảy ra trên bản đã commit trước phần LT (`test_audit` ×2, `test_autostart`, `test_resilience`, `test_supervisor`, `test_workspace`), không do adapter.

## 2. Việc cần làm

Có năm hạng mục. Thứ tự làm đề xuất ở mục 4.

### H1. Dọn bản sao trùng trong thư mục upstream

**Vấn đề.** Còn mã LT nằm trong `autocad-beiming-mcp-custom/` (đều là file chưa theo dõi, không gây xung đột git, nhưng gây nhầm):

| File | Tình trạng |
|---|---|
| `src/autocad_mcp/lt_window.py` | Giống hệt bản trong `lt-adapter/py/lt_adapter/` |
| `src/autocad_mcp/backends/lt_file_ipc.py` | Bản cũ 407 dòng; bản adapter là 505 dòng, lệch 114 dòng |
| `src/autocad_mcp/lt_verify.py` | Chỉ có ở đây, adapter không có bản nào |
| `tests/test_lt_backend.py`, `test_lt_verify.py`, `test_lisp_balance.py`, `test_lt_adapter.py`, `manual_lt_verification.py` | File LT mới trong thư mục tests của upstream |

`test_lt_backend.py` và `manual_lt_verification.py` đang import **bản cũ** (`autocad_mcp.backends.lt_file_ipc`), nên test đạt nhưng không chứng minh được bản đang chạy thật.

**Hướng xử lý.**
1. Xóa `src/autocad_mcp/lt_window.py` và `src/autocad_mcp/backends/lt_file_ipc.py`. Bản trong `lt-adapter/` là bản chuẩn. (File chưa theo dõi nên không ảnh hưởng git.)
2. Chuyển `lt_verify.py` sang `lt-adapter/py/lt_adapter/lt_verify.py`.
3. Chuyển các test LT sang `lt-adapter/tests/`, đổi import sang `lt_adapter.*`. Thư mục `autocad-beiming-mcp-custom/tests/` chỉ còn test upstream và test cục bộ cũ. Phương án thay thế: giữ test tại chỗ, chỉ đổi import (tiện chạy chung nhưng vẫn là file LT trong thư mục upstream).
4. Đổi import trong `test_lt_backend.py` thành `from lt_adapter.lt_file_ipc import LtFileIPCBackend` và chạy lại. **Chưa biết** bản adapter có đạt các test mà bản cũ đang đạt hay không; phải chạy mới biết.
5. Cập nhật `UPSTREAM_NOTES.md`, `lt-adapter/README.md` và `.gitignore`: cách chạy test (cần `PYTHONPATH` gồm `lt-adapter/py` và `autocad-beiming-mcp-custom/src`).
6. `launcher/cad_adapter.py` đã trỏ vào `lt-adapter/py/lt_adapter/lt_window.py`, nên xóa bản trùng không làm hỏng launcher.

**Hoàn thành khi:** thư mục `autocad-beiming-mcp-custom/` không còn file LT nào; toàn bộ test LT chạy từ `lt-adapter/` và đạt.

### H2. Nhãn lỗi sai (E_INTERNAL cho lỗi tham số)

**Nguyên nhân.** Các lệnh LISP của LT trả `(cons nil "thông báo")`, không có mã lỗi. `errors.py` của upstream (`infer_error_code`) đoán mã từ từ khoá trong thông báo; thông báo LT không khớp từ khoá nào nên thành `E_INTERNAL`, `recoverable: true`, gợi ý "inspect logs and retry". Agent có thể thử lại cùng yêu cầu sai nhiều lần. Một số thông báo có chữ `dispatcher` lại bị gắn sai thành `E_DISPATCHER_NOT_LOADED`.

Đã gặp trên LT thật: tên block trùng và lô xóa có handle không tồn tại đều trả `E_INTERNAL`.

**Hướng xử lý (toàn bộ trong adapter, không sửa upstream).**
1. Trong `lisp/mcp_dispatch_lt.lsp`, thay `(cons nil "message")` bằng `"E_xxx|message"`. Có khoảng 40 chỗ trả lỗi cần gắn mã.
2. Trong `lt_file_ipc.py`, sau khi nhận kết quả từ `_dispatch_unlocked`, tách tiền tố `E_xxx|` ra `error_code` và `error`. Không có tiền tố thì giữ hành vi cũ.
3. Dùng các mã đã có trong `ERROR_ACTIONS` của upstream để `recoverable` và `recommended_action` đúng:

| Nhóm lỗi trong LISP | Mã |
|---|---|
| Thiếu hoặc sai tham số, tên trùng, handle không hợp lệ, layer 0 | `E_PARAMETER_REJECTED` |
| Layer không tồn tại | `E_LAYER_NOT_FOUND` |
| Biến hệ thống bị từ chối | `E_VARIABLE_REJECTED` |
| Bản vẽ đã đổi trước lệnh | `E_DOCUMENT_ID_MISMATCH` |
| Bản vẽ nguồn không phải `source_path` | `E_SOURCE_DOCUMENT_MISMATCH` (backend đã dùng sẵn) |
| Lệnh LT thất bại và đã rollback | `E_BATCH_ROLLED_BACK` |
| Hatch lệch diện tích, hatch bị xóa | `E_POSTCONDITION_MISMATCH` |

4. Mỗi mã có một test: thông báo thô từ LISP được ánh xạ đúng sang mã và `recoverable`; chuỗi không có tiền tố vẫn hoạt động như cũ.
5. Chạy lại trên LT thật các trường hợp đã thử: tên block trùng, handle không tồn tại, `continue_on_error=true`.

**Lưu ý.** Sửa nhiều chỗ trong LISP, nên chạy `test_lisp_balance.py` sau mỗi lượt sửa (lỗi thiếu `)` đã xảy ra hai lần). Cách thay thế là mở rộng bảng từ khoá, không đề xuất vì thông báo đổi là mã sai ngay.

**Hoàn thành khi:** các lỗi tham số trả `E_PARAMETER_REJECTED` (hoặc mã tương ứng), `recoverable: false`, gợi ý đúng; test mới đạt; kiểm chứng lại trên LT.

### H3. Nhiễu COM

**Nguyên nhân.** Upstream viết nhiều tool kiểu "thử COM trước, lỗi thì rơi về LISP" (`_create_with_com_fallback` cho mọi `create_*`, `entity_get`...). Trên LT, COM chắc chắn lỗi, nên mỗi lần gọi mất một vòng gọi COM thừa và kết quả kèm `com_fallback` hoặc `warning: COM query unavailable...`, khiến agent tưởng có sự cố.

**Hướng xử lý (trong adapter).**
1. Override `_create_with_com_fallback` trong `LtFileIPCBackend` để đi thẳng vào `_dispatch`, gắn `renderer: "autolisp"`, không kèm `com_fallback`. Một override phủ tất cả `create_*`.
2. Override `entity_get` để gọi thẳng `entity-get` qua LISP, bỏ `warning`.
3. Phân loại các tool còn lại trong nhóm "có cả COM và LISP": `entity_trim`, `entity_extend`, `entity_join`, `layer_set_properties`, `create_dimension_linear/aligned/angular/radius`, `drawing_save`, `drawing_plot_pdf`, `drawing_audit`, `zoom_extents`. Mỗi tool: viết nhánh LISP, hoặc thêm vào `_UNSUPPORTED` (trả `E_NOT_SUPPORTED_ON_LT` ngay). Danh sách `_UNSUPPORTED` hiện có trong `lt_file_ipc.py` (18 tool) chưa gồm các tool này.
4. **Test chặn quay lại:** quét mọi method công khai của `FileIPCBackend`; method nào gọi helper COM thì bắt buộc thuộc một trong ba nhóm: đã override, nằm trong `_UNSUPPORTED`, hoặc nằm trong danh sách "đã xác nhận không dùng COM". Method mới chưa phân loại làm test đỏ.

**Chưa biết.** Với từng tool ở mục 3, LISP có làm được tương đương không; phải làm từng tool và chạy thật trên LT. Làm theo `LT_TOOL_PLAN.md`.

**Hoàn thành khi:** gọi `create_*` và `entity_get` trên LT không còn `com_fallback` hay cảnh báo COM; mọi tool có COM được phân loại; test quét đạt.

### H4. Phụ thuộc vào upstream

**Vấn đề.** Adapter dựa vào tên và cấu trúc upstream: `mcp-dispatch-command`, `c:mcp-dispatch`, `FileIPCBackend._dispatch_unlocked`, `client._backend`, `_init_lock`, `get_backend`, `ensure_backend_ready`, `config.detect_backend`, `config.LISP_DIR`. Hiện chỉ có một test staging bắt trường hợp đổi tên hàm dispatcher; phần còn lại chỉ ghi trong README, không có gì tự động kiểm tra. Nếu upstream đổi, lỗi có thể chỉ lộ khi chạy thật.

Ghi chú: ngày 22/10/2026 upstream `HEAD` vẫn là commit baseline `11f7c47e` (không có commit mới), nên chưa có xung đột thật; việc này là phòng ngừa.

**Hướng xử lý.**
1. **Test hợp đồng:** kiểm tra mọi thứ adapter dùng: symbol Python (class, method, thuộc tính, chữ ký hàm bị override), symbol LISP (hàm dispatcher, hàm JSON), tên tool bị thay (`delete_batching`, `copy_region_between_dwgs`). Thất bại thì nói rõ chỗ nào đổi.
2. **Ghim baseline:** lưu hash của `mcp_dispatch.lsp` và commit upstream trong adapter; hash đổi thì test báo "upstream đã thay đổi, cần rà adapter" thay vì lỗi mơ hồ.
3. **Thất bại an toàn khi khởi động:** `bootstrap.install()` chạy kiểm tra nhẹ trước khi vá. Nếu hợp đồng không khớp thì không cài adapter, ghi cảnh báo rõ vào log, để luồng AutoCAD đầy đủ chạy như cũ thay vì hỏng cả server.
4. **Một nguồn sự thật:** danh sách symbol nằm trong một bảng duy nhất; `lt-adapter/README.md` lấy từ đó.

**Hoàn thành khi:** đổi tên một symbol upstream (thử trên bản sao) làm test hợp đồng đỏ với thông báo rõ; hợp đồng không khớp thì server vẫn lên bằng đường AutoCAD đầy đủ.

### H5. Lỗi mới tìm thấy: chọn vùng phụ thuộc khung nhìn

**Vấn đề.** `region-preview-lt` và `region-copy-lt` chọn đối tượng bằng `ssget "_W"`/`"_C"`. Với khung nhìn bị thu nhỏ cực đại (`VIEWSIZE` ≈ 4×10⁹, đã gặp trong bản vẽ thử), kết quả là 0 đối tượng dù chúng nằm trong vùng chọn; sau khi zoom về vùng làm việc mới chọn được. Trên bản vẽ thật ở khung nhìn tương tự, tool có thể báo "Region is empty" mà không rõ lý do.

**Hướng xử lý.**
- Ưu tiên: chọn bằng `ssget "X"` kèm bộ lọc, rồi tự kiểm tra hộp bao (`window` = hộp bao nằm hoàn toàn trong vùng; `crossing` = hộp bao giao với vùng). Cách này không phụ thuộc khung nhìn.
- Phương án thay thế: lưu khung nhìn, zoom tạm tới vùng chọn, chọn, rồi khôi phục. Đơn giản nhưng đổi trạng thái hiển thị của người dùng.
- Thêm test: chạy lại kịch bản đã thử (khung nhìn rất lớn, 2 đối tượng trong vùng, 1 đối tượng xa) và kiểm tra preview chọn đúng 2.

**Hoàn thành khi:** preview chọn đúng số đối tượng ở cả khung nhìn bình thường lẫn khung nhìn thu nhỏ cực đại, trên LT thật.

## 3. Rủi ro chung

- Mọi thay đổi trong `mcp_dispatch_lt.lsp` cần `test_lisp_balance.py` và một lần nạp thật trên LT.
- Gateway và `stdio_bridge` giữ mã đã nạp; sau khi sửa phải khởi động lại launcher.
- Chỉ ghi lên bản vẽ thử. Cách dựng hai bản vẽ thử đã thử thành công: lưu bản vẽ thử bằng `(command "_.SAVEAS" "2018" path)` với `FILEDIA=0`, tạo bản đích bằng cách copy file rồi mở bằng `vla-Open` (lệnh `_.NEW` thất bại vì máy không có template `.dwt`, `(command "_.OPEN")` qua LISP không mở được). Phải trả `FILEDIA` về 1 sau khi dùng.
- Không commit, không push, không xóa gì ngoài phạm vi đã nêu khi chưa có yêu cầu rõ của người dùng.

## 4. Thứ tự làm đề xuất

| Bước | Việc | Lý do đặt ở đây |
|---|---|---|
| 1 | H1: dọn file trùng, chuyển test sang adapter | Làm test đáng tin trước khi sửa tiếp |
| 2 | H4: test hợp đồng upstream | Chạy được ngay, cho biết còn thiếu gì |
| 3 | H3: bỏ nhiễu COM, phân loại tool | Đổi hành vi nhiều tool, cần test quét bảo vệ |
| 4 | H2: nhãn lỗi | Sửa nhiều chỗ trong LISP; làm sau khi tập tool ổn định |
| 5 | H5: chọn vùng không phụ thuộc khung nhìn | Sửa độc lập, kiểm chứng trên LT thật |

Sau mỗi bước: chạy lại bộ test LT, và với tool bị đổi hành vi thì chạy lại trên LT thật.

## 5. Đã chốt và chưa chốt

- Đã chốt: thư mục adapter là `lt-adapter/`; nhánh vẽ cung `AddArc` trong `file_ipc.py` là sửa đổi có từ trước, không thuộc LT, không đụng vào.
- Resolved: LT-specific tests and verification helpers are stored in `lt-adapter/`.

## 6. Implementation status (2026-10-22)

- H1 complete: LT backend duplicates were removed from the vendored source. Verification helpers, LT tests, and the manual LT verifier now live under `lt-adapter/`; all 17 original LT tests pass from the new location.
- H4 complete: `lt-adapter/contract.json` records the upstream commit, dispatcher SHA-256, required Python/LISP symbols, signatures, and replacement tool modules. Bootstrap validates the contract before applying imports; drift emits a warning and leaves the upstream server path untouched. A drift simulation reports the changed hash.
- H3 complete in code and tests: creation and entity readback use AutoLISP without Python COM. COM-dependent operations without LT implementations return `E_NOT_SUPPORTED_ON_LT`. The AST coverage test fails when a public COM-dependent method is not overridden, explicitly unsupported, or documented as cleanup-only.
- H2 complete in code and tests: adapter LISP failures carry explicit error-code prefixes; the backend maps them to message, code, recoverability, and recommended action. Unprefixed upstream errors retain their existing inference behavior.
- H5 implemented and statically tested: preview and copy share an `_X` Model Space scan and WCS bounding-box filter, independent of zoom. Live verification on LT with both a normal and extremely zoomed-out view remains pending.
- Adapter suite: 57 passed. `compileall` and real-LT integration checks must run after restarting the launcher so the live server loads these changes. The existing launcher process was still active during this implementation, so no second dispatcher was started against the same LT session.
