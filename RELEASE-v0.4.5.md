AutoCAD MCP Launcher v0.4.5

# Tiếng Việt

Thêm nút **Tự thêm vào agent**: bấm một lần là launcher tự ghi cấu hình ba MCP (`autocad_puran`, `autocad_beiming`, `dutoan`) vào agent, không còn phải sao chép rồi dán tay.

Thêm:

- **Tab Điều khiển:** hai nút **Tự thêm vào agent** và **Gỡ khỏi agent** cho OpenAI Codex, Claude Code, Claude Desktop và **Cursor** (mới có trong ô Agent). Trước khi ghi, launcher hiện tệp sẽ sửa và từng mục sẽ làm gì (thêm mới, đã đúng, hay đang khác nên thay), rồi hỏi xác nhận. Tệp cũ được sao lưu vào `launcher\state\config-backups\`. Chỉ ba mục của launcher bị đụng tới; MCP khác của bạn giữ nguyên. Bấm lại khi đã đúng thì không ghi gì.
- **Claude Code:** chạy `claude mcp add --transport http --scope user …` (phạm vi user, dùng ở mọi project; cần lệnh `claude` trên PATH). Sau khi chạy, launcher đọc lại cấu hình để chắc mục đã vào, không tin mã thoát của lệnh.
- **Codex:** sửa `~/.codex/config.toml`, giữ nguyên kiểu xuống dòng, kiểm lại TOML trước khi ghi (Python 3.11 trở lên). Chỉ thay bảng chính của ba mục (và bảng con `.env`); **giữ** các bảng con của bạn như `[mcp_servers.<tên>.tools.<tool>]` với `approval_mode`. Gỡ thì bỏ cả bảng chính lẫn bảng con của ba mục đó, vì bảng con đứng một mình không hợp lệ.
- **Claude Desktop:** gộp vào `claude_desktop_config.json`, tự chọn tệp của bản cài thường (`%APPDATA%\Claude`) hoặc bản Store (`%LOCALAPPDATA%\Packages\Claude_*\LocalCache\Roaming\Claude`). Xong phải thoát hẳn và mở lại Claude Desktop.
- **Cursor:** gộp vào `%USERPROFILE%\.cursor\mcp.json`.
- Tệp cấu hình hỏng (JSON hoặc TOML không hợp lệ) thì launcher **không sửa** và báo lý do.

Thay đổi:

- Lệnh Claude Code trong ô "Sao chép cấu hình" nay có `--scope user`, giống nút tự thêm.
- Cửa sổ cao hơn để ô cấu hình không bị ép nhỏ; thông báo kết quả gọn một câu ("Đã cập nhật 3 mục: … Thoát hẳn Claude Desktop rồi mở lại.").

Cần làm:

- **Thoát hẳn launcher rồi mở lại**, rồi mở **phiên agent mới**.
- Máy đã ghi cấu hình bằng tay: bấm **Tự thêm vào agent** để đồng bộ (mục nào đã đúng thì giữ nguyên). Cấu hình trỏ tới thư mục cài của launcher đã bấm nút; đổi thư mục cài thì bấm lại.

Giới hạn:

- Project có `.mcp.json` riêng khai báo cùng tên thì cấu hình của project đó được ưu tiên hơn cấu hình user của Claude Code.
- Đã thử bằng test trên tệp tạm, trên bản sao `config.toml` Codex thật, với lệnh `claude mcp` thật dùng thư mục cấu hình tạm, và giao diện thật với ngữ cảnh tạm. **Đã ghi thật một lần vào Claude Desktop bản Store**: tệp hợp lệ và Claude Desktop liệt kê ba connector. **Chưa thử ghi thật** vào Cursor, Codex, Claude Code, và chưa thử kết nối thật tới gateway sau khi ghi.
- Trên Python 3.10 không có bước kiểm TOML sau khi sửa Codex.
- Các giới hạn khác giữ như v0.4.4 (cổng chặn skill chưa thử với Claude Code, Codex, Claude Desktop thật; `dutoan` qua HTTP chưa thử với `dutoan.db` thật 109 MB).

# English

Adds the **Tự thêm vào agent** (add to agent) button: one click and the launcher writes the configuration of the three MCPs (`autocad_puran`, `autocad_beiming`, `dutoan`) into the agent, with no more copying and pasting by hand.

Added:

- **Control tab:** two buttons, **Tự thêm vào agent** and **Gỡ khỏi agent** (remove), for OpenAI Codex, Claude Code, Claude Desktop and **Cursor** (new in the Agent box). Before writing, the launcher shows which file it will change and what it will do for each entry (add, already correct, or different and will be replaced), then asks for confirmation. The old file is backed up to `launcher\state\config-backups\`. Only the launcher's three entries are touched; your other MCPs stay as they are. Pressing it again when everything is correct writes nothing.
- **Claude Code:** runs `claude mcp add --transport http --scope user …` (user scope, works in every project; needs the `claude` command on PATH). After running, the launcher re-reads the configuration to confirm the entries are there instead of trusting the command's exit code.
- **Codex:** edits `~/.codex/config.toml`, keeps the line-ending style, and re-validates the TOML before writing (Python 3.11 and later). Only the main table of the three entries (and the `.env` sub-table) is replaced; **your own sub-tables are kept**, such as `[mcp_servers.<name>.tools.<tool>]` with `approval_mode`. Removing drops both the main table and the sub-tables of those three entries, because a sub-table on its own is invalid.
- **Claude Desktop:** merges into `claude_desktop_config.json`, choosing the regular install (`%APPDATA%\Claude`) or the Store build (`%LOCALAPPDATA%\Packages\Claude_*\LocalCache\Roaming\Claude`) automatically. Quit Claude Desktop completely and reopen it afterwards.
- **Cursor:** merges into `%USERPROFILE%\.cursor\mcp.json`.
- A broken configuration file (invalid JSON or TOML) is **not modified**; the launcher says why.

Changed:

- The Claude Code command in the "Sao chép cấu hình" (copy configuration) box now carries `--scope user`, like the button.
- The window is taller so the configuration box is no longer squeezed; the result message is one short sentence ("Đã cập nhật 3 mục: … Thoát hẳn Claude Desktop rồi mở lại.").

To do:

- **Quit the launcher completely and reopen it**, then start a **new agent session**.
- If you wrote the configuration by hand: press **Tự thêm vào agent** to sync (entries that are already correct are left alone). The configuration points at the install folder of the launcher whose button was pressed; press it again if you change the install folder.

Limitations:

- A project with its own `.mcp.json` declaring the same name takes precedence over Claude Code's user configuration.
- Tried with tests on temporary files, on a copy of a real Codex `config.toml`, with the real `claude mcp` command using a temporary configuration folder, and with the real UI against a temporary context. **One real write to the Store build of Claude Desktop was made**: the file is valid and Claude Desktop lists the three connectors. **Real writes to Cursor, Codex and Claude Code were not tried**, nor a real connection to the gateway after writing.
- On Python 3.10 there is no TOML re-validation step after editing Codex.
- Other limitations as in v0.4.4 (the skill gate not tried with real Claude Code, Codex or Claude Desktop; `dutoan` over HTTP not tried with the real 109 MB `dutoan.db`).
