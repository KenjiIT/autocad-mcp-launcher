# Kế hoạch sắp xếp lại cấu trúc thư mục dự án

Ngày lập: 23/10/2026. Repo: `C:\Users\minhk\orca\projects\MCP Deploy`. Nhánh: `feature/custom-beiming-mcp`.
Người nhận: agent thực hiện. Đọc hết mục 1 và 2 trước khi làm bất cứ việc gì.

## 1. Quy tắc bắt buộc

1. **Không gọi MCP AutoCAD** (`autocad_beiming`, `autocad_puran`, gateway cổng 8764). Có task khác đang dùng. Mọi việc dưới đây chỉ là thao tác file và test Python. Nếu cần gọi MCP, dừng lại và hỏi người dùng.
2. **Không đóng, không động vào tiến trình AutoCAD LT và các bản vẽ đang mở.** Không khởi động lại launcher/gateway khi chưa hỏi.
3. **Chưa commit, chưa push.** Chỉ commit khi người dùng yêu cầu. Nếu được yêu cầu, thông điệp commit kết thúc bằng
   `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`; mô tả PR kết thúc bằng `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
4. **Trước khi sửa:** chạy `git status --short` và giữ nguyên mọi thay đổi không liên quan (nhiều file chưa commit là của người dùng và của phiên trước).
5. **Không xoá gì** ngoài việc được liệt kê và đã được người dùng cho phép. Ưu tiên di chuyển (`git mv` với file đã theo dõi, `Move-Item` với file chưa theo dõi) hơn xoá.
6. **Không sửa mã upstream** trong `autocad-beiming-mcp-custom/src` (bản chép từ `beiming183-cloud/AutoCAD-MCP`, baseline `11f7c47e5038796a20451b38b23032e625b5aa26`).
7. **Không đụng nội dung bản vẽ** `.dwg`. Không mở bằng AutoCAD.
8. Không đưa việc "đã sửa file" thành "đã hoạt động": chỉ báo cái đã kiểm chứng (test chạy, lệnh trả gì) và nói rõ cái chưa kiểm chứng.
9. Người dùng nói tiếng Việt; báo cáo bằng tiếng Việt, ngắn gọn.

## 2. Bối cảnh

- `autocad-beiming-mcp-custom/`: bản chép (vendored, không có `.git` riêng) của Beiming AutoCAD MCP. Có 6 file nguồn bị sửa cục bộ: `audit.py`, `base.py`, `file_ipc.py`, `com_sta.py`, `native_pipe.py`, `server.py` (ghi ở `LOCAL_CHANGES.md`). `file_ipc.py` còn một nhánh `AddArc` của người khác, không thuộc việc LT.
- `lt-adapter/`: lớp phủ cho AutoCAD LT, có `contract.json` và `tests/`.
- `launcher/`: ứng dụng + gateway (cổng 8764); `launcher_multi/`: launcher thử nghiệm nhiều phiên.
- Thư mục chứa dữ liệu công việc của người dùng, **không được commit hay xoá**: `.agents/skills/autocad-identify-and-measure/`, `ErrorReports/`, `T3_dam_can_xac_nhan_dau_mut.csv`, `review_1852-T3-S-405/`, `tmp/`, `llmwiki/` (và `.llmwiki/`).
- Test adapter (đang 56 đạt, 0 lỗi), chạy từ `autocad-beiming-mcp-custom`:
  ```bash
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="src;../lt-adapter/py" .venv/Scripts/python.exe -m pytest ../lt-adapter/tests -q -p no:cacheprovider
  ```
  Bộ test upstream có 6 lỗi có sẵn từ trước phần LT (`test_audit`×2, `test_autostart`, `test_resilience`, `test_supervisor`, `test_workspace`): đừng tính là lỗi mới.
- Interpreter: gateway cần Python có `httpx`. Dùng `autocad-beiming-mcp-custom\.venv\Scripts\python.exe`/`pythonw.exe`, **không** dùng Python hệ thống.

## 3. Các việc, theo thứ tự thực hiện

Mỗi bước: làm, chạy "Kiểm tra", báo kết quả, rồi mới sang bước tiếp. Bước đánh dấu **[CẦN HỎI]** phải có xác nhận của người dùng trước khi làm.

### Bước 1 — Ngăn commit nhầm dữ liệu công việc (nhẹ, không di chuyển)
- Thêm vào `.gitignore` gốc: `/review_1852-T3-S-405/`, `/tmp/`, `/ErrorReports/`, `/T3_dam_can_xac_nhan_dau_mut.csv`.
- Không di chuyển, không xoá các mục đó.
- Kiểm tra: `git status --short` không còn liệt kê 4 mục trên ở dạng `??`; các thay đổi khác không đổi.
- **[CẦN HỎI]** nếu muốn gom chúng vào `work/`: phải rà trước xem skill, tài liệu hay script nào tham chiếu đường dẫn cũ (`grep -rn` các tên trên trong `.codex`, `.claude`, `.agents`, `docs`, `launcher`, `llmwiki`), báo danh sách rồi chờ xác nhận. Người dùng từng dặn không đụng vào các mục này.

### Bước 2 — Gom tài liệu kế hoạch LT về một chỗ
- Hiện có: `docs/LT_ADAPTER_PLAN.md`, `docs/LT_HARDENING_PLAN.md` (đã theo dõi hoặc chưa tuỳ file) và `autocad-beiming-mcp-custom/docs/LT_TOOL_PLAN.md`, `LT_VERIFY.md`, `LT_VERIFY_PLAN.md` (chưa theo dõi).
- Dời cả 5 file vào `docs/lt/`; tạo `docs/README.md` làm mục lục (một dòng mô tả mỗi file, gồm cả `claude-multi-session-autocad.md` và `PROJECT_LAYOUT_PLAN.md`).
- Sửa mọi liên kết chéo giữa các file này và trong `lt-adapter/README.md`, `README.md`, `UPSTREAM_NOTES.md` (dùng `grep -rn "LT_.*PLAN\|LT_VERIFY"` để tìm).
- Cập nhật mục 6 của `LT_HARDENING_PLAN.md`: ghi "56 đạt" (không phải 57; giảm 1 do bỏ `layer_set_properties` khỏi `_UNSUPPORTED`), và thêm ba việc làm sau đó chưa có test riêng: `entity-list-lt` (toạ độ), `layer_set_properties` trên LT, `launcher/acad_pid.py`. Ghi rõ "chưa có test tự động".
- Kiểm tra: không còn liên kết gãy (grep tên file cũ không ra kết quả); chạy lệnh test ở mục 2, vẫn 56 đạt.

### Bước 3 — Gọn thư mục gốc (phiên bản phát hành, script khởi động)
- Dời `RELEASE-v0.1.0.md`…`RELEASE-v0.1.3.md` vào `docs/releases/` bằng `git mv`. Trước đó grep xem `scripts/build_portable.py`, `installer/*`, `launcher/updater.py` có đọc đường dẫn này không; nếu có thì sửa theo, và nếu thấy rủi ro thì dừng, báo lại.
- Ba cách khởi động ở gốc (`start.ps1`, `Start AutoCAD MCP.cmd`, `Start AutoCAD MCP.vbs`): **không dời** (installer và người dùng có thể dựa vào). Chỉ thêm một đoạn "Cách khởi động" vào `README.md` nói rõ cái nào là chính. Đọc nội dung ba file trước khi viết.
- `dist/*.zip` (5 file) đang được git theo dõi: **[CẦN HỎI]** có ngừng theo dõi (`git rm --cached` + thêm `/dist/*.zip` vào `.gitignore`) hay chuyển sang GitHub Releases. Không làm khi chưa có câu trả lời. Lưu ý lịch sử git vẫn giữ bản cũ.
- `.harness/`, `.llmwiki/`, `.overstack.yaml`, `.pre-commit-config.yaml`, `CAPABILITIES.md`, `.github/workflows/harness.yml`, `.claude/settings.json`: **[CẦN HỎI]** có thuộc dự án này không. Không commit, không ignore, không xoá cho đến khi có câu trả lời.
- Kiểm tra: `git status --short` không bất ngờ; `python -m compileall launcher scripts` không lỗi mới.

### Bước 4 — Trùng lặp giữa `launcher/` và `launcher_multi/`
- Đã kiểm: `beiming_batch_copy.py`, `beiming_region_copy.py`, `beiming_timeout.py` **giống hệt** giữa `launcher/` và `launcher_multi/extensions/`; `beiming_delete_batch.py` **khác**.
- Việc: chạy `diff` hai bản `beiming_delete_batch.py`, xác định bản nào mới hơn và khác ở đâu, báo người dùng. **[CẦN HỎI]** trước khi hợp nhất.
- Đề xuất sau khi được duyệt: `launcher_multi/extensions/*.py` import từ `launcher/` (hoặc một mô-đun dùng chung) thay vì giữ bản sao; kiểm tra `launcher_multi/serve_session.py` cách nạp extension để không làm hỏng. Giữ `launcher_multi` ở trạng thái thử nghiệm (nó không có mã nào ngoài chính nó gọi tới, chỉ `docs/claude-multi-session-autocad.md` nhắc tới).
- Không chạy `launcher_multi` (nó sẽ khởi động tiến trình MCP, gây xung đột với task đang chạy).
- Kiểm tra: `python -m compileall launcher_multi`; đọc lại import, không chạy thật.

### Bước 5 — Lập danh sách chính xác "khác upstream ở đâu" (chỉ lập danh sách)
- Clone upstream vào thư mục tạm **nằm ngoài repo** (scratchpad hoặc `%TEMP%`), checkout `11f7c47e5038796a20451b38b23032e625b5aa26`.
- So `autocad-beiming-mcp-custom` (trừ `.venv`, `output`, `.local-data`, `lisp-code/.mcp_dispatch_*_runtime_*.lsp`, `__pycache__`) với bản gốc bằng `diff -rq`. Ghi kết quả vào `autocad-beiming-mcp-custom/LOCAL_CHANGES.md`: mỗi file một dòng, phân loại "sửa nguồn upstream" / "thêm mới" / "thiếu so với upstream", kèm lý do nếu biết.
- **Không** chuyển mã vào lớp phủ trong bước này.
- Kiểm tra: danh sách khớp 6 file đã biết; nếu có file lạ, báo nguyên văn.

### Bước 6 — Thư mục bản vẽ làm việc
- **[CẦN HỎI]** Hai bản `CR8-3_T3_he_truc.dwg` đang tồn tại: `autocad-beiming-mcp-custom/output/drawings/` (22/10 17:55, 111782 byte, đang mở trong LT) và `.local-data/output/drawings/` (19/10, 66097 byte). **Không xoá, không dời, không mở.** Chỉ đề xuất cho người dùng: đặt thư mục chuẩn cho bản vẽ làm việc và ghi chú trong README bản nào là bản chính.

## 4. Báo cáo cuối

Khi xong, báo theo mẫu:
- Bước đã làm / bước bỏ qua (lý do).
- File đã đổi (`git status --short` trước và sau).
- Kết quả test (số đạt/lỗi) và các lỗi có sẵn.
- Việc đã kiểm chứng vs chưa kiểm chứng.
- Các câu **[CẦN HỎI]** còn mở.

## 5. Thứ tự và độ rủi ro

| Bước | Rủi ro | Cần hỏi người dùng |
|---|---|---|
| 1 | Thấp | Chỉ khi muốn dời vào `work/` |
| 2 | Thấp | Không |
| 3 | Trung bình (đường dẫn trong installer/script) | `dist/*.zip`; công cụ ngoài |
| 4 | Trung bình | Hợp nhất `beiming_delete_batch.py` |
| 5 | Thấp (chỉ đọc + ghi tài liệu) | Không |
| 6 | Thấp (chỉ đề xuất) | Bản nào là bản chính |
