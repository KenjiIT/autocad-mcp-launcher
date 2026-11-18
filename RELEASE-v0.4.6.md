AutoCAD MCP Launcher v0.4.6

# Tiếng Việt

Bản này thêm **chế độ agent kết nối ra server** (tùy chọn), giúp agent **tự lấy và nạp skill chuyên biệt**, và sửa nhiều lỗi khi vẽ trục, dim và khối lượng lớn qua MCP.

Thêm:

- **Kết nối ra server (agent từ xa), tắt mặc định:** tab Cài đặt có mục **Kết nối ra server**. Launcher chủ động mở kết nối `wss://` **đi ra** tới server và chuyển lời gọi MCP server gửi xuống vào gateway nội bộ; không mở cổng nào ở máy này. Server chỉ gọi được `/beiming/mcp`, `/puran/mcp`, `/dutoan/mcp`; tool `launcher_set_backend` bị chặn với server; cổng buộc đọc skill vẫn áp dụng. Token không hiện lại sau khi lưu và không vào log. Đặc tả: `docs/GIAO-THUC-AGENT-KET-NOI-RA.md`.
- **Agent tự nạp skill chuyên biệt:** hướng dẫn của gateway và ghi chú agent nay có "Bước nạp skill tự động": sau skill điều phối, agent đọc bảng chọn và nạp các skill khớp việc. Nếu máy của agent chưa có bộ skill, agent đề nghị chép vào kho skill của chính nó (Claude Code `~/.claude/skills`, Codex CLI `~/.codex/skills`, agent khác thì thư mục skill riêng, không có thì `~/.agents/skills`); hỏi người dùng một lần, không ghi đè skill người dùng đã sửa.
- **Phát hiện bản vẽ bị sửa tay:** khi người dùng sửa bản vẽ ngoài agent, lệnh ghi kế tiếp báo `E_DOCUMENT_REVISION_MISMATCH` kèm `external_change_detected` để agent đọc lại trước khi vẽ tiếp. (Không thấy được sửa mà không đổi số đối tượng, `HANDSEED` và vùng bao.)
- **Skill dựng trục và dim:** thêm `references/truc-va-dim.md` vào `autocad-start-construction-drawing` (cách bản CR8-2B dựng trục: dim giữa trục dùng vạch xiên, không mũi tên, không đường gióng; thứ tự dựng; con số ở 1:100; các bẫy). Skill điều phối thêm dòng cho việc dựng trục và dim, cùng mục vẽ khối lượng lớn theo lô.

Sửa:

- **`cad_batch`:** nhận tham số ở cả `params` lẫn cấp ngoài cho từng thao tác; thiếu tham số thì báo `E_PARAMETER_REJECTED` có gợi ý, không còn `KeyError 'entity_id'` / `'x1'`.
- **Dim tạo qua công cụ:** `create_dimension_linear/aligned/angular/radius` nhận `layer` và `text`; dim mới lấy `DIMSCALE` của bản vẽ (trước đây `ScaleFactor` = 1 nên chữ nhỏ gấp 100 lần).
- **AutoCAD bận:** đọc `Application.HWND` thử lại khi AutoCAD đang bận, hết báo sai `E_AUTOCAD_INSTANCE_UNVERIFIED` sau vài lệnh vẽ.

Cần làm:

- **Thoát hẳn launcher rồi mở lại** (các sửa mã ở trên chỉ có hiệu lực sau khi gateway và Beiming khởi động lại), rồi mở **phiên agent mới**.
- Dùng Claude Desktop: tải lại hai skill `autocad-agent-coordinator` và `autocad-start-construction-drawing` (bản zip dựng lại trong `dist\`) ở Cài đặt, mục Skills.

Giới hạn:

- Kết nối ra server: đã thử bằng test với server WebSocket giả và một lượt chạy toàn tuyến trên gateway thật (`ws://` localhost). **Chưa thử** với server `wss://` thật và chứng chỉ TLS thật, với lệnh AutoCAD thật qua kênh này, và chạy nhiều giờ.
- Công cụ vẫn chưa chọn được kiểu đầu dim hay bỏ đường gióng; việc đó làm bằng COM ngoài MCP (đã ghi trong skill). Phát hiện sửa tay có giới hạn như trên.
- Việc agent tự chép skill là hướng dẫn cho mô hình, chưa kiểm với Claude Code, Codex, Claude Desktop thật.
- Bài kiểm "một bản launcher" (`test_launcher_single_instance`) báo lỗi khi đang có launcher chạy trên máy; đã chạy khi launcher mở. Các giới hạn khác giữ như v0.4.5.

# English

This release adds an optional **outbound agent mode**, makes agents **fetch and load specialist skills on their own**, and fixes several problems when drawing grids, dimensions and large drawings through MCP.

Added:

- **Outbound connection to a server (remote agent), off by default:** the Settings tab has a new **Kết nối ra server** section. The launcher opens an **outgoing** `wss://` connection to your server and relays the MCP calls it sends into the internal gateway; no port is opened on this machine. The server can only call `/beiming/mcp`, `/puran/mcp`, `/dutoan/mcp`; `launcher_set_backend` is blocked for it; the skill-read gate still applies. The token is never shown again after saving and never logged. Spec: `docs/GIAO-THUC-AGENT-KET-NOI-RA.md`.
- **Agents load specialist skills automatically:** the gateway instructions and the agent note now carry an "automatic skill loading" step: after the coordinator skill, the agent reads its table and loads the matching skills. If the agent's machine lacks the skill set, it offers to copy it into its own skill store (Claude Code `~/.claude/skills`, Codex CLI `~/.codex/skills`, other agents their own skill folder, else `~/.agents/skills`); it asks the user once and never overwrites skills the user edited.
- **Detect manual edits:** when the user edits the drawing outside the agent, the next write call returns `E_DOCUMENT_REVISION_MISMATCH` with `external_change_detected` so the agent re-reads before continuing. (Edits that keep the object count, `HANDSEED` and extents unchanged are not seen.)
- **Grid and dimension skill:** added `references/truc-va-dim.md` to `autocad-start-construction-drawing` (how the CR8-2B drawing builds grids: dimensions between grids use oblique ticks, no arrowheads, no extension lines; build order; 1:100 numbers; pitfalls). The coordinator skill gains a table row for grid and dimension work and a section on drawing large volumes in batches.

Fixed:

- **`cad_batch`:** accepts parameters both inside `params` and at the top level of each operation; missing parameters give `E_PARAMETER_REJECTED` with a hint instead of `KeyError 'entity_id'` / `'x1'`.
- **Dimensions made through the tool:** `create_dimension_linear/aligned/angular/radius` accept `layer` and `text`; new dimensions take the drawing's `DIMSCALE` (before, `ScaleFactor` was 1 so text came out 100 times too small).
- **Busy AutoCAD:** reading `Application.HWND` retries while AutoCAD is busy, ending the false `E_AUTOCAD_INSTANCE_UNVERIFIED` after a few drawing commands.

To do:

- **Quit the launcher completely and reopen it** (the code fixes above only take effect after the gateway and Beiming restart), then start a **new agent session**.
- On Claude Desktop: re-upload the two skills `autocad-agent-coordinator` and `autocad-start-construction-drawing` (rebuilt zips in `dist\`) under Settings, Skills.

Limitations:

- Outbound mode: tried with tests against a fake WebSocket server and one end-to-end run on a real gateway (`ws://` localhost). **Not tried** with a real `wss://` server and real TLS certificate, with real AutoCAD commands through this channel, or over many hours.
- The tool still cannot choose the dimension arrowhead type or suppress extension lines; that is done through COM outside MCP (documented in the skill). Manual-edit detection has the limits above.
- Agents copying skills on their own is guidance for the model; not tried with real Claude Code, Codex or Claude Desktop.
- The "single launcher instance" test (`test_launcher_single_instance`) fails while a launcher is running on the machine; it was run with the launcher open. Other limitations as in v0.4.5.
