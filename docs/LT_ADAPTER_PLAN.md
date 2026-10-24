# Kế hoạch tách luồng AutoCAD LT ra adapter (để cập nhật upstream không xung đột)

Ngày lập: 22/10/2026. Repo: `C:\Users\minhk\orca\projects\MCP Deploy`. Nhánh: `feature/custom-beiming-mcp`.
Tài liệu liên quan: `autocad-beiming-mcp-custom/docs/LT_TOOL_PLAN.md`, `autocad-beiming-mcp-custom/docs/LT_VERIFY_PLAN.md`, `llmwiki/wiki/sources/handover/211026-autocad-lt-agent.md`.

## 1. Mục tiêu

Đưa toàn bộ phần AutoCAD LT ra khỏi các file upstream của Beiming, vào một thư mục adapter riêng, để thư mục `autocad-beiming-mcp-custom/` quay về "upstream + sửa đổi cục bộ cũ". Khi cần lấy bản upstream mới thì chỉ phải xử lý các sửa đổi cục bộ cũ, không phải xử lý thêm phần LT.

Bối cảnh: `autocad-beiming-mcp-custom` là bản sao vendored (không có metadata git của upstream). Baseline: commit `11f7c47e5038796a20451b38b23032e625b5aa26` của `beiming183-cloud/AutoCAD-MCP` (xem `UPSTREAM_NOTES.md`). `LOCAL_CHANGES.md` ghi các sửa đổi cục bộ có từ trước phần LT.

## 2. Quyết định đã chốt

- Thư mục adapter: `lt-adapter/` ở gốc repo, cạnh `launcher/`.
- Nhánh vẽ cung (`AddArc`) trong `entity_create_lines_file` ở `file_ipc.py` là sửa đổi có từ trước, không thuộc LT. Không đụng vào, không đưa vào adapter.
- Không commit, không push, không xóa gì khi chưa có yêu cầu rõ của người dùng.
- Chỉ ghi lên bản vẽ thử. Không dùng DWG công việc.
- Mã đã "viết" không có nghĩa là đã "chạy được". Mọi tuyên bố "hoạt động" phải kèm kết quả chạy thật trên LT.

## 3. Hiện trạng (22/10/2026)

### Đã chạy thật trên LT 2027
- `system.ensure_ready` và `drawing.context` qua backend trực tiếp và qua gateway (cổng 8764): `ok=true`, `transport=file_ipc_lt`, dispatcher 4.0.0.
- `TRUSTEDPATHS` trong LT đã có `autocad-beiming-mcp-custom\lisp-code`.
- Bốn tool LT chưa chạy: hatch, `delete_batching`, `block.define`, `copy_region_between_dwgs`.

### Lỗi đã tìm và sửa trong phiên này (cần giữ khi chuyển sang adapter)
1. `mcp_dispatch.lsp` thiếu hai dấu `)`: trong `mcp-cmd-entity-delete-batch` và nhánh `CIRCLE` của `mcp-cmd-block-define-lt`. LT báo `malformed list on input`, dispatcher không nạp được và chỉ thấy timeout.
2. LT ghi ký tự ngoài cp1252 thành `\U+XXXX` (đúng 4 chữ số hex) trong file kết quả. Python không đọc được JSON nên chờ đến timeout. Đã sửa bằng `_lisp_unicode_to_json` trong `backends/file_ipc.py`. Regex phải là đúng 4 chữ số; viết 4–6 chữ số sẽ nuốt nhầm chữ cái hex đứng sau (ví dụ `việc` thành `vi𞱼`).
3. Gateway chạy bằng Python của `puran-water-autocad-mcp`, nơi `autocad_mcp` là package khác, nên `import autocad_mcp.backends.lt_file_ipc` lỗi và gateway trả `AUTOCAD_UNAVAILABLE`. Đã sửa bằng module độc lập `src/autocad_mcp/lt_window.py` (chỉ thư viện chuẩn + pywin32), nạp theo đường dẫn file từ `launcher/cad_adapter.py:find_lt_window()`.

### Danh sách file thay đổi cho LT
Sửa file upstream (đều chưa commit): `autocad-beiming-mcp-custom/lisp-code/mcp_dispatch.lsp`, `src/autocad_mcp/backends/file_ipc.py` (chỉ phần unicode; phần `AddArc` là của người khác), `src/autocad_mcp/client.py`, `src/autocad_mcp/config.py`, `src/autocad_mcp/custom_tools/batch_delete.py`, `src/autocad_mcp/custom_tools/region_copy.py`, `README.md` (gốc), `autocad-beiming-mcp-custom/README.md`.
Sửa file launcher (không phải upstream, giữ nguyên): `launcher/cad_adapter.py`, `launcher/gateway.py`.
File mới: `src/autocad_mcp/backends/lt_file_ipc.py`, `src/autocad_mcp/lt_window.py`, `tests/test_lt_backend.py`, `tests/test_lisp_balance.py`, `docs/LT_*.md`.
File không liên quan LT, không đụng: `.agents/skills/autocad-identify-and-measure/`, `ErrorReports/`, `T3_dam_can_xac_nhan_dau_mut.csv`, `review_1852-T3-S-405/`, `tmp/`, `llmwiki/`.

## 4. Cách tách

| Thay đổi hiện nằm trong file upstream | Chuyển vào `lt-adapter/` bằng cách |
|---|---|
| `mcp_dispatch.lsp` (hàng trăm dòng LT) | File `lt-adapter/lisp/mcp_dispatch_lt.lsp`. Lưu bản gốc `mcp-dispatch-command` thành `mcp-dispatch-command-upstream`, định nghĩa lại để xử lý lệnh LT và gọi lại bản upstream cho lệnh khác. Kiểm tra `_expected_document_path` đặt trong bản bọc của `c:mcp-dispatch`. Backend LT nạp file upstream trước, rồi nạp file này. |
| `lt_file_ipc.py` | Chuyển vào `lt-adapter/py/lt_adapter/lt_file_ipc.py` |
| `lt_window.py` | Chuyển vào `lt-adapter/py/lt_adapter/lt_window.py`; `launcher/cad_adapter.py` đổi đường dẫn nạp |
| Sửa `file_ipc.py` (unicode) | Backend LT tự có `_dispatch_unlocked` đọc kết quả có gọi `_lisp_unicode_to_json`. Không sửa `file_ipc.py`. Lỗi này chỉ gặp ở LT. |
| Sửa `client.py`, `config.py` (chọn `file_ipc_lt`) | `launcher/serve.py` (hoặc `lt-adapter/py/lt_adapter/bootstrap.py` do `serve.py` gọi) đặt hook trước khi nạp `autocad_mcp.server`: thay `detect_backend`, `get_backend`, `ensure_backend_ready` để chọn `LtFileIPCBackend` khi chỉ có LT chạy. |
| Sửa `batch_delete.py`, `region_copy.py` | Adapter đăng ký lại hai tool `delete_batching` và `copy_region_between_dwgs` (tương tự `launcher/beiming_*.py`), rẽ nhánh LT, còn AutoCAD đầy đủ giữ đường COM. |

Hiện `serve.py` chỉ đăng ký `beiming_*.py` khi tên repo bắt đầu bằng `beiming183`. Thư mục hiện tại không khớp nên các bản đó không chạy. Adapter mới phải được đăng ký bất kể tên repo.

## 5. Các bước làm

Mỗi bước kết thúc bằng một lần chạy thật; không sang bước tiếp theo khi bước trước chưa đạt.

**Bước 0 – Sao lưu và đo hiện trạng (30 phút)**
- Lưu diff hiện tại: `git diff -- autocad-beiming-mcp-custom launcher > tmp/lt_state_before_adapter.patch` và chép các file mới (`lt_file_ipc.py`, `lt_window.py`) sang `tmp/`. Đây là lưới an toàn để hoàn tác.
- Chạy `tests/test_lisp_balance.py` và `tests/test_lt_backend.py`. Ghi lại kết quả nền (cần cài `pytest` vào `.venv` nếu chưa có).
- Xác nhận `ensure_ready` qua gateway vẫn `ok=true`.

**Bước 1 – Dựng `lt-adapter/` và chuyển backend (1–2 giờ)**
- Tạo `lt-adapter/py/lt_adapter/` với `lt_window.py` và `lt_file_ipc.py`. Sửa import trong hai file để không còn phụ thuộc `autocad_mcp.lt_window` mà vẫn dùng `autocad_mcp.backends.file_ipc.FileIPCBackend` (class gốc).
- Thêm `_dispatch_unlocked` riêng cho LT (có `_lisp_unicode_to_json`), thay cho sửa ở `file_ipc.py`.
- Cập nhật `launcher/cad_adapter.py` để nạp `lt_window.py` từ vị trí mới.
- Kiểm tra: gọi trực tiếp backend (như script `lt_probe.py` đã dùng), kết quả phải khớp hôm trước, kể cả đường dẫn tiếng Việt `C:\Công việc\...`.

**Bước 2 – Chuyển LISP (1–2 giờ)**
- Tạo `lt-adapter/lisp/mcp_dispatch_lt.lsp` theo bảng trên. Giữ nguyên các hàm `mcp-cmd-*-lt` đã có (document-context, entity-delete-batch, create-hatch-lt, block-define-lt, region-preview-lt, region-copy-lt).
- Backend LT nạp thêm file này sau file upstream.
- Chạy `test_lisp_balance.py` cho cả hai file `.lsp` (lỗi thiếu `)` đã xảy ra hai lần).
- Kiểm tra: nạp trên LT thật, `ping` và `document-context` trả `ok`.

**Bước 3 – Hook chọn backend và đăng ký tool (2–3 giờ, rủi ro cao nhất)**
- Hai điểm chưa kiểm chứng: (a) vá `detect_backend`/`get_backend` có tác dụng không nếu `server.py` đã import tên hàm; (b) FastMCP có thay tool khi đăng ký trùng tên không, hay giữ tool cũ. Phải thử thật; nếu giữ tool cũ thì gỡ khỏi bộ quản lý tool trước khi đăng ký.
- Hạn chế: không để adapter làm hỏng đường AutoCAD đầy đủ. Khi có cửa sổ `acad.exe` thì vẫn chọn `file_ipc`.
- Kiểm tra: khởi động qua `launcher/serve.py`, gọi `system.get_backend` và `system.ensure_ready` qua gateway; backend phải là `file_ipc_lt`.

**Bước 4 – Khôi phục file upstream (30 phút)**
- Chỉ làm khi người dùng đồng ý rõ. Khôi phục `lisp-code/mcp_dispatch.lsp`, `client.py`, `config.py`, `batch_delete.py`, `region_copy.py` về bản đã commit bằng `git checkout -- <file>`. Với `file_ipc.py` chỉ bỏ phần unicode, giữ phần `AddArc` của người khác (khôi phục thủ công, không `git checkout` cả file).
- Chạy lại toàn bộ kiểm tra bước 1–3.

**Bước 5 – Kiểm chứng bốn tool LT trên bản vẽ thử (2–4 giờ)**
- Theo `LT_VERIFY_PLAN.md`: tạo bản vẽ thử bằng `entmake`, đọc lại trạng thái bằng lệnh LISP chỉ-đọc, không dựa vào COM. Thứ tự: hatch (đối chiếu diện tích), `delete_batching` (handle đúng và sai), `block.define` (LINE/CIRCLE/ATTDEF), `copy_region_between_dwgs` (preview rồi copy giữa hai DWG cùng phiên LT).

**Bước 6 – Tài liệu (30–60 phút)**
- Ghi vào `UPSTREAM_NOTES.md` quy trình cập nhật upstream: sao lưu → thay thư mục upstream → áp lại các sửa đổi cục bộ cũ → chạy kiểm tra adapter.
- Ghi `lt-adapter/README.md`: cách hook hoạt động và những tên hàm upstream mà adapter phụ thuộc (`mcp-dispatch-command`, `c:mcp-dispatch`, `FileIPCBackend._dispatch_unlocked`, `client.get_backend`).
- Sửa mục LT trong `README.md` gốc.

## 6. Môi trường và cách chạy

- LT: `C:\Program Files\Autodesk\AutoCAD LT 2027\acadlt.exe`. Cần mở một bản vẽ (màn hình Start thì LISP không chạy). Đặt `AUTOCAD_MCP_ACAD_PID` khi có nhiều cửa sổ LT.
- Python của backend Beiming: `autocad-beiming-mcp-custom\.venv\Scripts\python.exe` (chưa có `pytest`, cần cài).
- Python của gateway: `puran-water-autocad-mcp\.venv\Scripts\python.exe`. Trong môi trường này `autocad_mcp` là package của Puran, nên không import `autocad_mcp.*` của Beiming từ gateway.
- Mở launcher: `%APPDATA%\uv\python\cpython-3.12-windows-x86_64-none\pythonw.exe "...\launcher\run_app.py"`. Gateway nghe cổng 8764, đường dẫn `/beiming/mcp` (POST JSON-RPC, header `Accept: application/json, text/event-stream`). Gateway và `stdio_bridge` giữ code đã nạp, nên phải khởi động lại launcher sau khi sửa file.
- Gọi thử: `tools/call` với `name="system"`, `arguments={"operation":"ensure_ready"}`.
- Kết quả đúng của LT: `transport="file_ipc_lt"`, `autocad.product="AutoCAD LT"`.
- Dòng lệnh LT nhận lệnh gõ qua `PostMessageW(WM_CHAR)` tới cửa sổ con có lớp `MDIClient`. Gửi tới cửa sổ chính thì không tới LT.

## 7. Rủi ro và việc chưa kiểm chứng

- Nhánh chọn `file_ipc` khi AutoCAD đầy đủ đang chạy chưa được kiểm tra live vì phiên này chỉ có AutoCAD LT.
- Tốc độ copy 5.000 đối tượng và chi phí nạp lại dispatcher mỗi lần gọi chưa đo.
- Hộp thoại lỗi giấy phép Autodesk ("Unable to connect with a Licensing component") đã xảy ra một lần; dịch vụ `AdskLicensingService` khi kiểm tra vẫn chạy.
- Phiên MCP của agent cần kết nối lại sau khi launcher chạy lại; kết quả `AUTOCAD_UNAVAILABLE` từng gặp có thể là kết nối cũ.
- Cả launcher, gateway và backend LT hiện chạy trên cùng LT PID; nếu mở thêm LT thứ hai, backend từ chối đoán và trả lỗi, đó là hành vi có chủ ý.

Đã thử trên LT 2027 trong phiên này: hatch bằng `AddHatch`, copy vùng bằng `vla-CopyObjects`, mở và chuyển giữa hai DWG trong cùng một LT, probe độc lập và xóa entity theo lô. Chi tiết nằm trong `tmp/lt-adapter-20261022/VERIFICATION.md`.

## 8. Việc đi kèm (không chặn, xem `LT_TOOL_PLAN.md`)

- Chặn lỗi sớm cho tool COM-only trên LT (`E_NOT_SUPPORTED_ON_LT`) thay vì timeout.
- Đưa `system.preflight` vào nhánh LT (hiện bắt buộc `win32com` và profile registry R25 của AutoCAD đầy đủ).
- Khai báo khả năng (`capabilities`/danh sách tool không hỗ trợ) trong `ensure_ready` và `get_backend` của LT, và thêm `product` vào `/status` của gateway để agent phân biệt LT với AutoCAD đầy đủ.
- Cập nhật skill: `autocad-agent-coordinator` (dòng 36 ghi "COM-only"), `autocad-trace-floor-outline` (phụ thuộc `drawing.save_as_dxf`, `render_preview`, `activate`, `open`), `autocad-structural-floor-plan`. Ba thư mục skill `.claude`, `.agents`, `.codex` đang không đồng bộ.
- `launcher/beiming_*.py` là mã chết với tên repo hiện tại (chỉ đăng ký khi tên bắt đầu bằng `beiming183`). Nếu đổi tên thư mục thành `beiming183*` thì các bản COM này sẽ ghi đè tool LT; cần xóa hoặc chặn theo backend.

## 9. Tiêu chí hoàn thành

1. Partially met: LT-specific changes have been moved out of vendored upstream files. Full AutoCAD live compatibility remains unverified.
2. Đạt một phần: gateway trả `file_ipc_lt` trên LT; nhánh AutoCAD đầy đủ chưa có phiên live để xác minh.
3. Đạt: hatch, delete batching, block define và copy vùng chạy trên DWG thử; kết quả được đọc lại qua LISP/IPC.
4. Đạt một phần: `UPSTREAM_NOTES.md` đã có quy trình refresh; chưa diễn tập nâng upstream trên bản sao.

## 10. Kết quả thực hiện (22/10/2026)

- Bước 0: sao lưu diff và hai module LT vào `tmp/lt-adapter-20261022/`; focused tests nền đạt 14/14.
- Bước 1: tạo `lt-adapter/py/lt_adapter/` cho backend và định vị cửa sổ; launcher bootstrap chọn adapter và thay các module tool LT trước khi import server.
- Bước 2: đưa dispatcher LT vào `lt-adapter/lisp/mcp_dispatch_lt.lsp`. Runtime nạp dispatcher upstream đã đổi tên thành `mcp-dispatch-command-upstream`, rồi nạp overlay từ thư mục LISP được tin cậy. Overlay không có UTF-8 BOM.
- Bước 3: adapter import và backend selection chạy qua gateway trên AutoCAD LT; MCP tool list có hai tool bổ sung. Nhánh AutoCAD đầy đủ chưa được xác minh live.
- Step 4: COMPLETE. Restored upstream dispatcher, client, config, batch_delete, and region_copy to committed versions; removed only the LT Unicode decoder from file_ipc.py while preserving the pre-existing AddArc change.
- Bước 5: đã chạy bốn tool trên AutoCAD LT 2027 với bản vẽ thử và hai DWG sao chép trong `tmp/`; cả hai bản sao đóng mà không lưu.
- Bước 6: đã thêm `lt-adapter/README.md`, quy trình refresh vào `UPSTREAM_NOTES.md`, và cập nhật mục AutoCAD LT trong README gốc.
- Sau adapter-specific tests: `17 passed`; `compileall` đạt. Không có commit hoặc push.
