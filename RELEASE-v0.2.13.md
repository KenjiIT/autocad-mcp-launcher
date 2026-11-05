AutoCAD MCP Launcher v0.2.13

# Tiếng Việt

Sửa hai lỗi làm agent không mở được bản vẽ và bị khóa kênh khi đọc bản vẽ lớn, và cho agent biết thư mục tri thức chung đã tải về.

Sửa:

- **`drawing open` báo "opened" dù không mở được file** (AutoCAD đầy đủ). Mã gốc chạy `(command "_.OPEN" ...)` rồi luôn báo thành công, nên agent tưởng đã mở trong khi tab không đổi. Giờ mở bằng COM (`Documents.Open`), kích hoạt bản vẽ và **kiểm tra nó thật sự đang hoạt động**. File đã mở sẵn thì chỉ kích hoạt (`already_open: true`); đường dẫn không tồn tại báo `E_PARAMETER_REJECTED`; nếu phải dùng lệnh LISP dự phòng thì chờ tối đa 3 giây và báo `E_POSTCONDITION_MISMATCH` khi bản vẽ không hoạt động. Có vòng thử lại 10 giây khi AutoCAD bận, hạn mở 300 giây cho DWG lớn có xref. **AutoCAD LT giữ nguyên đường LISP cũ** (LT không có COM).
- **Hạn đọc 600 giây không được áp dụng**, nên `drawing.audit` bản vẽ lớn bị cắt sau 60 giây và khóa kênh COM (`COM STA worker is poisoned`) cho tới khi khởi động lại. Nguyên nhân: `launcher/serve.py` chỉ bật việc nới hạn cho thư mục tên bắt đầu bằng `beiming183`, nên mất tác dụng khi mã chuyển sang `autocad-beiming-mcp-custom`. README cũng ghi sai số giây; đã sửa theo mã (đọc 600, IPC 300, gateway chờ 720).

Thêm:

- **Tool MCP `knowledge`** (chỉ đọc): `index` liệt kê trang tri thức chung, `search` tìm theo từ khóa không cần gõ dấu, `get` đọc một trang. Đọc đúng thư mục `Tải tri thức` đã tải về (mặc định `~/autocad-knowledge`, hoặc `COMMON_KNOWLEDGE_DIR`), nên agent chạy trong môi trường bị giới hạn thư mục vẫn đọc được. Chỉ phục vụ `wiki/` (trang đã duyệt), không phục vụ `proposals/`.
- **Hướng dẫn gateway gửi cho mọi agent** và `AGENTS.md` nay nhắc agent tra tri thức chung trước khi làm việc mới. Trước đây không chỗ nào nói với agent rằng thư mục đó tồn tại.
- Skill `knowledge-query` ưu tiên dùng tool `knowledge`.
- `docs/HUONG-DAN-CAI-DAT-MAY-MOI.md`: hướng dẫn cài đặt máy mới và quy trình tri thức chung.

Cần làm:

- Tải lại lên Claude Desktop (Cài đặt, mục Skills) `knowledge-query.zip`.
- **Thoát hẳn launcher rồi mở lại**, bấm Bật kết nối cho agent, rồi **mở phiên agent mới** (agent giữ danh sách tool cũ trong phiên đang mở).

Giới hạn đã biết:

- Sửa mở file đã thử trên một máy với AutoCAD đầy đủ 2027 (mở file chưa mở, đã mở, không tồn tại). **Đường LT không được thử trên LT thật**; chỉ có test chứng minh LT không gọi COM.
- Hạn 600 giây chỉ áp dụng cho `drawing.audit` và `entity.collect`. Các thao tác đọc khác vẫn có hạn riêng (khoảng 30 đến 60 giây); quá hạn thì vẫn khóa kênh cho tới khi gọi `system init` hoặc khởi động lại MCP. Với DWG lớn hãy đọc từng layer.
- Chưa chạy lại lệnh `audit` của bản vẽ lớn đã gây lỗi để xem nó xong trong hạn mới.
- Trong bộ test của `autocad-beiming-mcp-custom` có 5 test hỏng sẵn từ trước, không liên quan và chưa sửa (ví dụ `test_audit`, `test_workspace`, `test_supervisor`, `test_resilience`). Các thay đổi lần này không làm thêm test hỏng.
- Tool `knowledge` chỉ đọc những gì đã tải; launcher vẫn không tự tải tri thức, phải bấm Tải tri thức.
- Chưa có trang tri thức về lỗi khóa kênh COM. Kế thừa từ v0.2.12: chưa thử bộ cài đóng gói trên máy thứ hai; bốn skill tri thức chưa chạy trong phiên thật với nhiều người; cổng nhận đề xuất chưa có giới hạn số đề xuất mỗi ngày; gateway (cổng 8764) không tự chạy sau khi Windows khởi động lại; bộ cài Windows chưa ký.

# English

Fixes two defects that stopped agents from opening drawings and locked the command channel when reading large drawings, and tells agents about the downloaded shared-knowledge folder.

Fixed:

- **`drawing open` reported "opened" even when the file did not open** (full AutoCAD). The upstream code ran `(command "_.OPEN" ...)` and always reported success, so agents believed a drawing was open while the tab did not change. It now opens through COM (`Documents.Open`), activates the drawing and **verifies it is really active**. An already open file is only activated (`already_open: true`); a missing path returns `E_PARAMETER_REJECTED`; when the AutoLISP fallback is used it waits up to 3 seconds and returns `E_POSTCONDITION_MISMATCH` if the drawing is not active. A 10 second retry covers a busy AutoCAD and the open deadline is 300 seconds for large drawings with xrefs. **AutoCAD LT keeps the previous AutoLISP route** (LT has no COM).
- **The 600 second read deadline was not applied**, so `drawing.audit` on a large drawing was cut off after 60 seconds and locked the COM channel (`COM STA worker is poisoned`) until a restart. Cause: `launcher/serve.py` enabled the extension only for a folder whose name starts with `beiming183`, which stopped matching once the code moved to `autocad-beiming-mcp-custom`. The README also stated the wrong number of seconds; corrected to the code (read 600, IPC 300, gateway wait 720).

Added:

- **MCP tool `knowledge`** (read only): `index` lists the shared-knowledge pages, `search` finds them by keyword without typing diacritics, `get` reads one page. It reads the folder filled by "Tải tri thức" (default `~/autocad-knowledge`, or `COMMON_KNOWLEDGE_DIR`), so agents sandboxed away from that folder can still read it. It serves only `wiki/` (reviewed pages), never `proposals/`.
- **The gateway instructions sent to every agent**, and `AGENTS.md`, now tell agents to consult the shared knowledge before new work. Nothing told agents that folder existed before.
- The `knowledge-query` skill prefers the `knowledge` tool.
- `docs/HUONG-DAN-CAI-DAT-MAY-MOI.md`: new-machine setup guide and the shared-knowledge workflow.

To do:

- Re-upload `knowledge-query.zip` to Claude Desktop (Settings, Skills).
- **Quit the launcher completely and reopen it**, press the connect button, then **open a new agent session** (agents keep their old tool list in an open session).

Known limitations:

- The open-file fix was tried on one machine with full AutoCAD 2027 (an unopened file, an open file, a missing file). **The LT route was not tried on real LT**; tests only prove LT does not call COM.
- The 600 second deadline applies only to `drawing.audit` and `entity.collect`. Other read operations keep their own deadlines (about 30 to 60 seconds); exceeding one still locks the channel until `system init` or an MCP restart. Read large drawings layer by layer.
- The `audit` that triggered the lock has not been re-run to confirm it now finishes within the new deadline.
- The `autocad-beiming-mcp-custom` test suite has 5 pre-existing failures that are unrelated and not fixed (for example `test_audit`, `test_workspace`, `test_supervisor`, `test_resilience`). These changes add no failing tests.
- The `knowledge` tool reads only what was downloaded; the launcher still does not download knowledge by itself.
- There is no knowledge page about the COM channel lock yet. Carried over from v0.2.12: the packaged installer has not been tried on a second machine; the four knowledge skills have not been run in a real session with several people; the submission gateway has no per-day cap; the gateway (port 8764) does not start by itself after Windows restarts; the Windows installer is unsigned.
