AutoCAD MCP Launcher v0.3.0

# Tiếng Việt

Agent biết lúc nào nên ghi lại điều học được, và lỗi đắt giá nay tự chỉ tới tri thức chung. Tri thức chung lên **v0.2.0** (9 trang) và đã chạy thật lần nâng cấp thứ hai.

Thêm:

- **Gợi ý trong lỗi (`hint`).** Khi kênh COM bị khóa (`E_COM_STA_TIMEOUT`, `E_COM_STA_UNAVAILABLE`) hoặc `drawing open` không xác minh được (`E_POSTCONDITION_MISMATCH`), kết quả lỗi có thêm trường `hint`: việc nên làm ngay và trang tri thức cần tra.
- **`AGENTS.md` mục 8, tự ghi điều học được theo sự kiện:** lỗi rồi tìm ra cách sửa, tool cư xử khác mô tả, người dùng chỉnh lại, phải thử nhiều cách mới ra, quy ước chưa ai ghi. Agent tra `knowledge` trước, rồi **hỏi người dùng một câu**; chỉ khi đồng ý mới ghi và gửi bằng `knowledge_propose`.
- **Skill `knowledge-capture`** có bảng sự kiện và ba thời điểm cân nhắc.
- **Tri thức chung v0.2.0** (đã được duyệt và đóng tag, launcher tự tải trong 24 giờ): thêm hai trang nhóm `cad-mcp`: *Kênh COM bị khóa sau một lệnh đọc quá hạn* và *drawing open báo "opened" nhưng bản vẽ không mở*. Đây là hai đề xuất do chính agent gửi qua cổng, đi hết chuỗi gửi, duyệt, đóng tag.

Cần làm:

- **Thoát hẳn launcher rồi mở lại**, rồi mở phiên agent mới (để agent nhận `AGENTS.md` và `hint` mới).
- Tải lại lên Claude Desktop `knowledge-capture.zip`.

Đã kiểm chứng: nâng cấp tri thức từ `v0.1.0` lên `v0.2.0` thật trên GitHub (đổi tag, xóa trang cũ, ghi lại `.version`); 47 test của `hint` và `drawing open` đạt.

Giới hạn đã biết:

- Câu "gọi `system` `operation=init` để dựng lại luồng COM" trong trang tri thức mới **chưa thử trên một kênh đang bị khóa thật** (chỉ đối chiếu mã nguồn).
- Chưa thử bộ cài đóng gói của v0.2.13 đến v0.3.0 trên máy thứ hai; chưa chạy lại `audit` bản vẽ lớn để xác nhận hạn đọc 600 giây; đường mở file trên LT chưa thử trên LT thật.
- `SENSITIVE_TERMS` chưa đặt ở kho tri thức; cổng Cloudflare chưa có hạn mức theo ngày; 5 test hỏng sẵn của bộ test beiming chưa sửa; bộ cài Windows chưa ký.

# English

Agents now know when to record what they learned, and costly errors point to the shared knowledge by themselves. The shared knowledge reaches **v0.2.0** (9 pages), and the second real upgrade has been run.

Added:

- **Hints in errors (`hint`).** When the COM channel is quarantined (`E_COM_STA_TIMEOUT`, `E_COM_STA_UNAVAILABLE`) or `drawing open` cannot be verified (`E_POSTCONDITION_MISMATCH`), the error result carries a `hint` field: what to do right away and which knowledge page to read.
- **`AGENTS.md` item 8, event-driven learning:** an error then a fix, a tool behaving differently from its description, a user correction, several attempts needed, an undocumented convention. The agent checks `knowledge` first, then **asks the user one question**; only with consent does it write and send through `knowledge_propose`.
- **`knowledge-capture` skill** gains the event table and the three moments to consider.
- **Shared knowledge v0.2.0** (reviewed and tagged; launchers fetch it within 24 hours): two new `cad-mcp` pages: *COM channel quarantined after an overdue read* and *drawing open reports "opened" but nothing opens*. Both were submitted by an agent through the gateway, completing the full submit, review, tag chain.

To do:

- **Quit the launcher completely and reopen it**, then open a new agent session (so agents receive the new `AGENTS.md` and `hint`).
- Re-upload `knowledge-capture.zip` to Claude Desktop.

Verified: a real knowledge upgrade from `v0.1.0` to `v0.2.0` on GitHub (tag change, stale page removed, `.version` rewritten); 47 tests for `hint` and `drawing open` pass.

Known limitations:

- The line "call `system` `operation=init` to rebuild the COM thread" in the new knowledge page has **not been tried on a truly quarantined channel** (checked against source only).
- The packaged installers from v0.2.13 to v0.3.0 have not been tried on a second machine; the large-drawing `audit` has not been re-run to confirm the 600 s deadline; the LT open route has not been tried on real LT.
- `SENSITIVE_TERMS` is not set on the knowledge repo; the Cloudflare gateway has no daily cap; 5 pre-existing failing beiming tests are not fixed; the Windows installer is unsigned.
