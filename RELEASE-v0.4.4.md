AutoCAD MCP Launcher v0.4.4

# Tiếng Việt

Gateway **buộc agent đọc skill điều phối trước khi dùng tool CAD**, và công cụ `dutoan` chuyển từ stdio sang **HTTP qua gateway**.

Thêm:

- **Cổng chặn skill.** Lời dặn "nạp skill trước" trong hướng dẫn MCP và trong `CLAUDE.md`/`AGENTS.md` chỉ là nhắc, nên agent hay bỏ qua. Nay gateway phát `Mcp-Session-Id` lúc `initialize`, và mọi tool CAD của `autocad_beiming`/`autocad_puran` trả lỗi `SKILL_NOT_READ` (kèm bước kế tiếp: gọi `skills` với `operation=get`, `name=autocad-agent-coordinator`) cho tới khi phiên đó đã đọc skill. Việc chặn xảy ra trước hàng đợi CAD. Không bị chặn: `skills`, `knowledge`, `knowledge_propose`, `launcher_set_backend` và toàn bộ `dutoan`. Chỉ việc đọc thân skill điều phối bằng tool `skills` mới được tính.
- **Tab Cài đặt:** ô "Buộc agent đọc skill điều phối trước khi dùng tool CAD" (mặc định bật, có hiệu lực ngay). Biến môi trường `AUTOCAD_MCP_SKILL_GATE=off` cũng tắt được.
- **`dutoan` qua gateway:** địa chỉ `http://127.0.0.1:8764/dutoan/mcp`. Gateway chạy riêng một tiến trình `dutoan` (cổng nội bộ 8877, stateless) cho mọi agent, tự khởi động ở lần gọi đầu tiên, không đi qua bộ chọn MCP AutoCAD nên không bị ngắt khi đổi giữa Beiming và Puran và không cần AutoCAD. Thêm `POST /dutoan/stop` và mục `dutoan` trong `/status`.

Thay đổi:

- **Cấu hình agent:** mục `dutoan` của Codex, Claude Code, Claude Desktop (qua `stdio_bridge.py dutoan`) và Cursor nay là địa chỉ HTTP, không còn đường dẫn Python. Nhãn trạng thái đổi thành "HTTP qua gateway".
- **Nhập hoặc tải `dutoan.db`:** trước khi thay tệp, launcher nhờ gateway thả tiến trình `dutoan` (đang giữ tệp) và xóa các tệp phụ `-wal`/`-shm` của bản cũ. Tiến trình tự khởi động lại ở lần gọi kế tiếp.
- **Tài liệu:** `README.md`, hướng dẫn cài `docs/HUONG-DAN-CAI-DAT-MAY-MOI.md` và `du-toan-mcp/README.md` cập nhật theo. Câu cũ "chưa phải cơ chế bắt buộc ở gateway" được sửa.

Cần làm:

- **Thoát hẳn launcher rồi mở lại**, rồi mở **phiên agent mới**.
- **Cấu hình lại `dutoan` ở mọi agent** đã dùng kiểu stdio: Claude Code chạy `claude mcp remove dutoan` rồi `claude mcp add --transport http dutoan http://127.0.0.1:8764/dutoan/mcp`; Codex thay mục `command = ...` bằng `url`; Claude Desktop thay mục `dutoan` bằng cấu hình sao chép mới từ launcher. Từ nay `dutoan` cần launcher đang chạy và đã **Bật kết nối cho agent**.

Giới hạn:

- Gateway chỉ buộc **một bước** (đọc skill điều phối). Nó không kiểm được agent có làm theo skill hay có nạp thêm các skill chuyên biệt hay không.
- Cổng chặn mới thử với client MCP của Python trên gateway thật (bị chặn khi chưa đọc, mở sau khi đọc, phiên mới bị chặn lại). **Chưa thử với Claude Code, Codex, Claude Desktop thật**; máy khách không gửi lại `Mcp-Session-Id` thì dùng chung cửa sổ 30 phút. Gateway khởi động lại thì mọi phiên phải đọc lại. Máy không có skill `autocad-agent-coordinator` thì cổng tự mở.
- `dutoan` qua HTTP mới thử với cơ sở dữ liệu tạm (`initialize`, `tools/list` đủ 12 tool, `tools/call`, dừng rồi tự khởi động lại). **Chưa thử với `dutoan.db` thật 109 MB**, chưa thử cầu nối `stdio_bridge.py dutoan` trên Claude Desktop, và chưa thử cả luồng **Nhập từ tệp…** trong cửa sổ launcher (mới thử từng phần bằng test).
- Các giới hạn khác giữ như v0.4.3.

# English

The gateway now **makes agents read the coordinator skill before using CAD tools**, and the `dutoan` tool moves from stdio to **HTTP through the gateway**.

Added:

- **Skill gate.** The "load the skill first" guidance in the MCP instructions and in `CLAUDE.md`/`AGENTS.md` is only a reminder, and agents often skip it. The gateway now issues an `Mcp-Session-Id` on `initialize`, and every CAD tool of `autocad_beiming`/`autocad_puran` returns a `SKILL_NOT_READ` error (with the next step: call `skills` with `operation=get`, `name=autocad-agent-coordinator`) until that session has read the skill. The refusal happens before the CAD queue. Not gated: `skills`, `knowledge`, `knowledge_propose`, `launcher_set_backend` and all of `dutoan`. Only reading the coordinator skill body through the `skills` tool counts.
- **Settings tab:** a checkbox "Buộc agent đọc skill điều phối trước khi dùng tool CAD" (on by default, effective immediately). The environment variable `AUTOCAD_MCP_SKILL_GATE=off` also turns it off.
- **`dutoan` through the gateway:** address `http://127.0.0.1:8764/dutoan/mcp`. The gateway runs one separate `dutoan` process (internal port 8877, stateless) for every agent, started on the first call. It bypasses the AutoCAD MCP switchboard, so it is not cut off when switching between Beiming and Puran and needs no AutoCAD. Adds `POST /dutoan/stop` and a `dutoan` entry in `/status`.

Changed:

- **Agent configuration:** the `dutoan` entry for Codex, Claude Code, Claude Desktop (via `stdio_bridge.py dutoan`) and Cursor is now an HTTP address, no longer a Python path. The status label now reads "HTTP qua gateway".
- **Importing or downloading `dutoan.db`:** before replacing the file, the launcher asks the gateway to drop the `dutoan` process (which holds the file) and removes the old database's `-wal`/`-shm` side files. The process restarts by itself on the next call.
- **Documentation:** `README.md`, the install guide `docs/HUONG-DAN-CAI-DAT-MAY-MOI.md` and `du-toan-mcp/README.md` are updated. The old sentence "not an enforced mechanism at the gateway" is corrected.

To do:

- **Quit the launcher completely and reopen it**, then start a **new agent session**.
- **Reconfigure `dutoan` in every agent** that used stdio: Claude Code runs `claude mcp remove dutoan` then `claude mcp add --transport http dutoan http://127.0.0.1:8764/dutoan/mcp`; Codex replaces the `command = ...` entry with `url`; Claude Desktop replaces the `dutoan` entry with the new configuration copied from the launcher. From now on `dutoan` needs the launcher running with **Bật kết nối cho agent** on.

Limitations:

- The gateway enforces **one step** only (reading the coordinator skill). It cannot check that the agent follows the skill or loads further specialised skills.
- The gate was only tried with the Python MCP client against a real gateway (refused before reading, open after reading, a new session refused again). **Not tried with real Claude Code, Codex or Claude Desktop**; a client that does not send `Mcp-Session-Id` back shares a 30-minute window. A gateway restart makes every session read again. On a machine without the `autocad-agent-coordinator` skill the gate stays open.
- `dutoan` over HTTP was only tried against a temporary database (`initialize`, `tools/list` with all 12 tools, `tools/call`, stop then automatic restart). **Not tried with the real 109 MB `dutoan.db`**, not with the `stdio_bridge.py dutoan` bridge on Claude Desktop, and the whole **Nhập từ tệp…** flow in the launcher window was not run (only parts, by test).
- Other limitations as in v0.4.3.
