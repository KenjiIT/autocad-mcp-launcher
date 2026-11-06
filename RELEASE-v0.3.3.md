AutoCAD MCP Launcher v0.3.3

# Tiếng Việt

Agent nay **tự gửi tri thức lên hàng chờ duyệt** mà không hỏi trước; tri thức chung lên **v0.3.0** (12 trang).

Đổi:

- **`AGENTS.md` mục 8 và skill `knowledge-capture`:** khi có sự kiện đáng ghi, agent tra `knowledge`, tự viết trang, gỡ tên dự án, tên khách hàng, mã dự án, số liệu thật, đường dẫn máy, chạy lint rồi gọi `knowledge_propose`, sau đó chỉ **báo người dùng một dòng**. Lint còn lỗi hoặc còn nghi ngờ một chi tiết nhạy cảm thì **không gửi**, giữ ở `proposals/` và hỏi. Người dùng dặn đừng gửi thì không gửi.
- Skill `knowledge-promote`, mô tả tool `knowledge_propose`, gợi ý `hint` trong lỗi và hướng dẫn cài đặt đổi theo.
- Chỗ chặn thật nay là **người duyệt**: trang chỉ công khai sau khi được đọc lại và đóng tag.
- **Tri thức chung v0.3.0:** thêm 3 trang nhóm `cad-mcp`: *cad_batch kẹt "Only one AutoCAD transaction may be active"*, *Điểm chèn của TEXT và MTEXT*, *Chữ tiếng Việt bị lỗi font khi ghi chú*. Do chính người duyệt đưa thẳng vào, không qua hàng chờ.

Cần làm:

- Thoát hẳn launcher rồi mở lại; mở phiên agent mới.
- Tải lại lên Claude Desktop `knowledge-capture.zip` và `knowledge-promote.zip`.
- Người duyệt: đọc kỹ từng đề xuất trước khi đóng tag, vì nay agent không hỏi trước khi gửi.

Giới hạn:

- Bộ lọc tự động chỉ bắt mẫu chung (email, số điện thoại, đường dẫn, khóa) và tên trong `sensitive-terms.local.txt`; `SENSITIVE_TERMS` chưa đặt ở kho chung. Agent gỡ sai một tên dự án thì chỉ người duyệt chặn được.
- Cổng Cloudflare chưa có hạn mức theo ngày, nên agent gửi nhiều có thể làm đầy hàng chờ.
- Các giới hạn khác giữ như v0.3.2.

# English

Agents now **submit knowledge to the review queue by themselves**, without asking first; shared knowledge reaches **v0.3.0** (12 pages).

Changed:

- **`AGENTS.md` item 8 and the `knowledge-capture` skill:** on a noteworthy event the agent checks `knowledge`, writes the page, strips project names, client names, project codes, real figures and machine paths, runs lint, calls `knowledge_propose`, then only **tells the user in one line**. If lint fails or a detail might be sensitive it **does not send**: it keeps the file in `proposals/` and asks. If the user said not to send, it does not.
- The `knowledge-promote` skill, the `knowledge_propose` tool description, the error `hint` and the setup guide follow.
- The real gate is now **the reviewer**: a page goes public only after being re-read and tagged.
- **Shared knowledge v0.3.0:** three new `cad-mcp` pages: *cad_batch stuck on "Only one AutoCAD transaction may be active"*, *Insertion point of TEXT and MTEXT*, *Vietnamese text shows wrong font*. Added directly by the reviewer, not through the queue.

To do:

- Quit the launcher completely and reopen it; start a new agent session.
- Re-upload `knowledge-capture.zip` and `knowledge-promote.zip` to Claude Desktop.
- Reviewers: read every proposal carefully before tagging, since agents no longer ask before sending.

Limitations:

- The automatic filter catches only generic patterns (e-mail, phone, paths, keys) and names in `sensitive-terms.local.txt`; `SENSITIVE_TERMS` is not set on the shared repo. If an agent strips a project name wrongly, only the reviewer stops it.
- The Cloudflare gateway has no daily cap, so an agent sending a lot could fill the queue.
- Other limitations as in v0.3.2.
