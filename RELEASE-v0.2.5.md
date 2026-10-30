AutoCAD MCP Launcher v0.2.5

# Tiếng Việt

Thêm:

- AutoCAD LT: lệnh `drawing save`. Lưu tại chỗ, hoặc lưu thành bản mới vào đường dẫn `.dwg` đầy đủ do người dùng chọn. File đích đã có thì lệnh từ chối (`E_FILE_EXISTS`); chỉ ghi đè khi truyền `overwrite=true` sau khi người dùng đồng ý. Chỉ báo thành công khi bản vẽ không còn thay đổi chưa lưu (`dbmod=0`). Lưu thành bản mới thì `doc_id` đổi, kết quả trả sẵn giá trị mới.
- Skill `autocad-agent-coordinator`: quy trình hỏi người dùng nơi lưu bằng hộp chọn rồi mới lưu; quy trình tạo bản vẽ mới trên LT (sao template `.dwt` của LT thành file `.dwg`, rồi `drawing open`, không dựng DXF hay DWG tối giản bằng mã).
- Khi một lệnh gửi vào AutoCAD LT chạy quá 25 giây, adapter ghi ngăn xếp của mọi luồng vào `C:\temp\lt_adapter_stall.log` để tìm nguyên nhân treo.

Sửa:

- AutoCAD LT bị đứng khoảng 5 phút: launcher cho mọi lệnh chờ tối đa 300 giây, nên một lệnh đọc nhẹ mà AutoCAD bỏ sót lần kích hoạt cũng giữ cả hàng đợi 5 phút. Nay lệnh đọc nhẹ (`document-context`, `ping`, kiểm tra layer, đọc biến) chờ tối đa 20 giây rồi trả lỗi `E_IPC_TIMEOUT`, và tự gõ lại phím kích hoạt đúng một lần sau 6 giây. Lệnh nặng giữ ngưỡng dài và không bị gõ lại phím.
- Bước gửi phím kích hoạt trước đây chạy đồng bộ trong vòng lặp sự kiện, nếu kẹt thì cả server đứng. Nay nó chạy ở luồng riêng, tối đa 20 giây, quá hạn thì trả `E_LT_TRIGGER_STALLED` kèm gợi ý nhấn Esc.
- Cửa sổ Help của AutoCAD tự bật liên tục khi phím kích hoạt rơi sai chỗ: adapter nay tự đóng cửa sổ Help lạ khi đang chờ kết quả, và với lệnh đọc nhẹ thì gõ lại phím ngay.
- Server MCP Revit không khởi động được trên Node 24 (thư viện `better-sqlite3` 11.x phải biên dịch từ mã nguồn mà máy không có Visual Studio). Launcher nay dùng bản cài cục bộ ở `%LOCALAPPDATA%\revit-mcp-server` với `better-sqlite3` 12.x, không còn phụ thuộc cache của `npx`; nếu chưa cài thì quay về `npx`.

Thay đổi:

- Chỉ tạo file DXF khi người dùng yêu cầu hoặc khi không có kết nối AutoCAD (skill điều phối, mặt bằng kết cấu, truy biên đường bao, bắt đầu bản vẽ; mô tả tool `launcher_set_backend`; `AGENTS.md`). AutoCAD đang kết nối thì làm trực tiếp trên DWG, không tự xuất bản sao DXF.
- Skill `mat-bang-tong-the` đã có từ v0.2.4; bản zip dựng lại cùng các skill khác.

Giới hạn đã biết:

- Chưa biết vì sao AutoCAD thỉnh thoảng bỏ sót phím kích hoạt dispatcher. Bản này rút thời gian treo từ 5 phút xuống tối đa 20 giây và đóng cửa sổ Help, nhưng chưa loại bỏ được lỗi; cách chữa tận gốc (gửi phím vào đúng ô dòng lệnh thay vì vùng chứa bản vẽ) chưa làm.
- Sau một lần quá thời gian, lệnh vẽ có thể đã chạy xong trong AutoCAD mà không báo về; agent phải đọc lại bản vẽ trước khi gửi lại để khỏi vẽ trùng (chưa có trong skill).
- AutoCAD LT vẫn không hỗ trợ đối tượng kích thước thật (`create_dimension_*`), `save_as_dxf`, tạo hoặc đóng bản vẽ qua MCP.
- Gateway (cổng 8764) không tự chạy sau khi Windows khởi động lại, kể cả khi launcher tự mở; cần bấm Start.
- Tab Revit và add-in vẫn chưa được thử với Revit đang mở thật.
- 6 test của `autocad-beiming-mcp-custom` thất bại trên máy chỉ có AutoCAD LT (cần AutoCAD đầy đủ, hoặc khác biệt hoa/thường trong đường dẫn); chúng thất bại như nhau khi bỏ thay đổi của bản này. Bộ test `lt-adapter` (104) đạt.
- Các bản vá treo mới chỉ được thử trên một máy.
- Kế thừa: bộ cài Windows chưa ký, SmartScreen có thể cảnh báo nhà phát hành không xác định.

# English

Added:

- AutoCAD LT: `drawing save`. Saves in place, or saves a copy to a full `.dwg` path chosen by the user. An existing target is refused (`E_FILE_EXISTS`); it is replaced only with `overwrite=true`, set after the user agreed. Success is reported only when the drawing has no unsaved changes (`dbmod=0`). Saving to a new path changes the `doc_id`; the result carries the new values.
- Skill `autocad-agent-coordinator`: how to ask the user where to save with a choice prompt before saving; how to create a new drawing on LT (copy an LT `.dwt` template to a `.dwg` file, then `drawing open`, with no hand-built DXF or minimal DWG).
- When a command sent to AutoCAD LT runs longer than 25 s, the adapter writes every thread's stack to `C:\temp\lt_adapter_stall.log` to find the cause of the hang.

Fixed:

- AutoCAD LT stalled for about 5 minutes: the launcher allows every command up to 300 s, so a light read that AutoCAD never picked up held the whole queue for 5 minutes. Light reads (`document-context`, `ping`, layer checks, variable reads) now wait at most 20 s and return `E_IPC_TIMEOUT`, and retype the trigger once after 6 s. Heavy commands keep the long cap and are not retyped.
- The trigger keystrokes used to run synchronously on the event loop, so a stalled step froze the whole server. They now run in a worker thread for at most 20 s and return `E_LT_TRIGGER_STALLED` with a hint to press Esc.
- AutoCAD's Help window kept opening when the trigger keys landed in the wrong place: the adapter now closes a stray Help window while waiting, and retypes the trigger at once for a light read.
- The Revit MCP server did not start on Node 24 (`better-sqlite3` 11.x had to be built from source and the machine has no Visual Studio). The launcher now uses a local install in `%LOCALAPPDATA%\revit-mcp-server` with `better-sqlite3` 12.x instead of relying on the npx cache, and falls back to `npx` when it is not installed.

Changed:

- DXF files are created only when the user asks, or when there is no AutoCAD connection (coordinator, structural floor plan, trace floor outline and start-construction-drawing skills; the `launcher_set_backend` tool text; `AGENTS.md`). With AutoCAD connected, work is done directly on the DWG and no DXF copy is exported on the agent's own initiative.
- Skill `mat-bang-tong-the` is unchanged since v0.2.4; its zip is rebuilt with the others.

Known limitations:

- It is not known why AutoCAD occasionally ignores the dispatcher trigger. This release shortens the stall from 5 minutes to at most 20 s and closes the Help window, but does not remove the fault; the root fix (sending keys to the actual command-line box instead of the drawing container) is not done.
- After a timeout, a drawing command may already have run in AutoCAD without reporting back; an agent must read the drawing again before resending to avoid drawing twice (not yet in the skill).
- AutoCAD LT still does not support real dimension objects (`create_dimension_*`), `save_as_dxf`, or creating and closing drawings through the MCP.
- The gateway (port 8764) does not start by itself after Windows restarts, even when the launcher does; press Start.
- The Revit tab and add-in have still not been tried against a running Revit.
- 6 tests of `autocad-beiming-mcp-custom` fail on a machine with only AutoCAD LT (they need full AutoCAD, or hit a path-case difference); they fail the same way without this release's changes. The `lt-adapter` suite (104 tests) passes.
- The hang fixes have only been tried on one machine.
- Carried over: the Windows installer is unsigned; SmartScreen may show an unknown publisher warning.
