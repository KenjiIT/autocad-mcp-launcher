AutoCAD MCP Launcher v0.3.5

# Tiếng Việt

Sửa việc agent **không tự đẩy tri thức lên**: quy tắc ghi và gửi nay đến được mọi agent, ở mọi dự án và mọi máy.

Nguyên nhân: quy tắc "tự ghi và gửi" chỉ nằm trong `AGENTS.md` của repo launcher và trong skill `knowledge-capture`. Agent làm việc ở thư mục dự án khác, hoặc trên máy cài bằng bộ cài, không đọc `AGENTS.md` này; lời hướng dẫn mà launcher gửi cho mọi agent khi kết nối chỉ dặn **đọc** tri thức, không dặn ghi. Skill điều phối `autocad-agent-coordinator` (agent nào cũng nạp trước) cũng không nhắc tới tri thức. Đường gửi (khóa, cổng, hàng chờ) vẫn chạy tốt; thiếu là lời dặn.

Đổi:

- **Hướng dẫn MCP của launcher** (agent nhận khi kết nối) thêm đoạn **ghi lại điều học được**: khi lỗi rồi có cách sửa, tool cư xử khác mô tả, người dùng chỉnh lại, hoặc gặp quy ước chưa ai ghi, thì tra `knowledge`, nếu chưa có thì gọi `knowledge_propose` với trang ngắn, không cần hỏi người dùng, gỡ thông tin dự án trước, còn nghi ngờ thì không gửi, gửi xong báo một dòng.
- **Skill `autocad-agent-coordinator`** thêm mục "Tri thức chung: tra và ghi".
- **Mô tả tool `knowledge_propose`** nay nói rõ nên gọi chủ động, không cần hỏi.

Cần làm:

- **Thoát hẳn launcher rồi mở lại**, rồi mở **phiên agent mới** (lời hướng dẫn chỉ nhận lúc bắt đầu phiên).
- Tải lại lên Claude Desktop `autocad-agent-coordinator.zip` nếu dùng skill ở đó.

Giới hạn:

- Đây là lời dặn cho mô hình, **không có gì ép buộc**; agent vẫn có thể bỏ qua khi bận việc khác. Chưa kiểm chứng được bằng một phiên agent thật sau khi sửa; sau khi cập nhật, hãy làm một việc có lỗi rồi xem hàng chờ có đề xuất mới không.
- Các giới hạn khác giữ như v0.3.4 (khóa nhúng sẵn chỉ là che giấu; cổng chưa có hạn mức theo ngày).

# English

Fixes agents **not pushing knowledge up**: the record-and-submit rule now reaches every agent, in every project and on every machine.

Cause: the "write and submit by yourself" rule lived only in the launcher repo's `AGENTS.md` and in the `knowledge-capture` skill. An agent working in another project folder, or on a machine installed from the setup exe, never reads this `AGENTS.md`; the instructions the launcher sends every agent on connect only said to **read** knowledge, not to record it. The coordinator skill `autocad-agent-coordinator` (loaded first by every agent) did not mention knowledge either. The submit path (key, gateway, queue) works; the instruction was missing.

Changed:

- **The launcher's MCP instructions** (received on connect) gain a **record what you learned** paragraph: after an error with a fix, a tool behaving differently from its description, a user correction, or an undocumented convention, check `knowledge`, and if it is missing call `knowledge_propose` with a short page, without asking the user, stripping project details first, not sending when in doubt, and reporting in one line afterwards.
- **The `autocad-agent-coordinator` skill** gains a "Tri thức chung: tra và ghi" section.
- **The `knowledge_propose` tool description** now says to call it proactively, without asking.

To do:

- **Quit the launcher completely and reopen it**, then start a **new agent session** (instructions are read only at session start).
- Re-upload `autocad-agent-coordinator.zip` to Claude Desktop if you use the skill there.

Limitations:

- This is guidance for the model, **nothing enforces it**; an agent can still skip it when busy. It has not been verified in a real agent session after the change; after updating, do a task that hits an error and check the queue for a new proposal.
- Other limitations as in v0.3.4 (the embedded key is only obscured; the gateway has no daily cap).
