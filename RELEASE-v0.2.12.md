AutoCAD MCP Launcher v0.2.12

# Tiếng Việt

Agent gửi được đề xuất tri thức chung từ launcher mà người dùng không cần tài khoản GitHub.

Thêm:

- **Tool MCP `knowledge_propose`** (gateway, cổng 8764): gửi một trang tri thức đề xuất tới cổng nhận đề xuất, cổng ghi vào một repo riêng tư để người duyệt đọc. Trang chưa công khai cho tới khi người duyệt chấp nhận. Launcher **kiểm tra trên máy trước khi gửi**: đầu trang, email, số điện thoại, đường dẫn máy, khóa, và các thuật ngữ trong `sensitive-terms.local.txt` (đặt trong thư mục tri thức). Trang bị chặn thì không có gì rời khỏi máy.
- **Tab Cài đặt, mục "Gửi đề xuất tri thức":** ô địa chỉ cổng (mặc định có sẵn) và ô khóa nhóm (ẩn khi gõ). Khóa lưu trong `launcher/state/settings.json` trên máy này. Có thể thay bằng biến môi trường `KNOWLEDGE_TEAM_KEY` và `KNOWLEDGE_GATEWAY_URL`.
- **Mã cổng `knowledge-gateway/`** (Cloudflare Worker, chạy được trên gói miễn phí) kèm hướng dẫn triển khai trong `knowledge-gateway/README.md`. Cổng kiểm tra khóa nhóm, kích thước, đầu trang và nội dung nhạy cảm, rồi mới ghi vào repo riêng tư.

Sửa:

- Skill `knowledge-capture` và `knowledge-promote` hỏi người dùng có gửi không, rồi gọi `knowledge_propose`; xử lý `NO_TEAM_KEY` và `REJECTED_LOCALLY`; vẫn có đường gửi tay khi không có tool. Đã đồng bộ ba bản skill và dựng lại zip.
- `scripts/build_portable.py` không còn gói thư mục `launcher/state` (chứa cài đặt riêng từng máy, kể cả khóa nhóm) khi dựng bản cục bộ. Bản phát hành do CI dựng từ repo sạch nên vốn không có thư mục này.

Cần làm:

- Tải lại lên Claude Desktop (Cài đặt, mục Skills) `knowledge-capture.zip` và `knowledge-promote.zip`. `knowledge-query.zip` và `knowledge-lint.zip` không đổi.
- Muốn gửi đề xuất: nhập khóa nhóm do người quản lý cấp ở tab Cài đặt, mục Gửi đề xuất tri thức. **Bản này không có khóa mặc định**, nên chưa nhập thì tool trả `NO_TEAM_KEY`.
- Khởi động lại gateway (tắt rồi bật MCP) để nhận tool mới.

Giới hạn đã biết:

- Đã chạy thử toàn chuỗi (gateway của launcher, kiểm tra trên máy, cổng, repo riêng tư) bằng khóa thật trên một máy, và chụp tab Cài đặt để xem giao diện. Chưa thử bản cài đặt đóng gói của v0.2.12 và chưa thử trên máy thứ hai.
- Bốn skill tri thức vẫn chưa chạy trong một phiên làm việc thật với người dùng.
- Cổng chưa có giới hạn số đề xuất mỗi ngày (cần gắn KV của Cloudflare); hiện chỉ có giới hạn 50 KB mỗi đề xuất. Người có khóa nhóm có thể làm đầy hàng chờ.
- Khóa nhóm dùng chung và nằm trên mỗi máy, nên không biết ai gửi (nhãn người gửi do người gửi tự khai) và khóa lộ thì phải đặt lại cho cả nhóm.
- Người duyệt vẫn làm thủ công: đọc hàng chờ, sửa, rồi đưa trang vào repo công khai bằng tay.
- Danh sách thuật ngữ nhạy cảm do từng người tự điền; kiểm tra không biết tên dự án mới.
- Kế thừa từ v0.2.11: chưa lập thử một dự toán hoàn chỉnh bằng `tra-dinh-muc-du-toan`; `thiet-ke-phong-nha` chưa chạy trên mặt bằng thật; tab Revit pyRevit chưa thử với Revit đang mở; gateway (cổng 8764) không tự chạy sau khi Windows khởi động lại; bộ cài Windows chưa ký.

# English

Agents can submit shared-knowledge proposals from the launcher without a GitHub account.

Added:

- **MCP tool `knowledge_propose`** (gateway, port 8764): sends a proposed knowledge page to a submission gateway, which writes it into a private repository for a reviewer. The page is not public until the reviewer accepts it. The launcher **checks the page on this machine before sending**: front matter, e-mail addresses, phone numbers, machine paths, keys, and the terms in `sensitive-terms.local.txt` (placed in the knowledge folder). A rejected page sends nothing off the machine.
- **Settings tab, "Gửi đề xuất tri thức" section:** a gateway address field (pre-filled) and a team key field (masked while typing). The key is stored in `launcher/state/settings.json` on this machine. The environment variables `KNOWLEDGE_TEAM_KEY` and `KNOWLEDGE_GATEWAY_URL` can override both.
- **Gateway source `knowledge-gateway/`** (a Cloudflare Worker that runs on the free plan) with deployment steps in `knowledge-gateway/README.md`. It checks the team key, size, front matter and sensitive content before writing to the private repository.

Changed:

- The `knowledge-capture` and `knowledge-promote` skills ask the user whether to send, then call `knowledge_propose`; they handle `NO_TEAM_KEY` and `REJECTED_LOCALLY`, and still offer a manual route when the tool is missing. All three skill copies are synced and the zips rebuilt.
- `scripts/build_portable.py` no longer packages the `launcher/state` folder (per-machine settings, including the team key) in local builds. Releases are built by CI from a clean checkout, which never had that folder.

To do:

- Re-upload `knowledge-capture.zip` and `knowledge-promote.zip` to Claude Desktop (Settings, Skills). `knowledge-query.zip` and `knowledge-lint.zip` are unchanged.
- To send proposals: enter the team key given by the administrator on the Settings tab, in the "Gửi đề xuất tri thức" section. **This release has no default key**, so the tool returns `NO_TEAM_KEY` until one is entered.
- Restart the gateway (stop and start MCP) to pick up the new tool.

Known limitations:

- The whole chain (launcher gateway, local check, gateway, private repository) was run with a real key on one machine, and the Settings tab was captured to check the layout. The packaged v0.2.12 installer and a second machine have not been tried.
- The four knowledge skills have still not been run in a real working session with a user.
- The gateway has no per-day submission cap yet (it needs Cloudflare KV); only the 50 KB per-proposal limit applies. Anyone with the team key can fill the queue.
- The team key is shared and stored on each machine, so the sender is unknown (the sender label is self-declared), and a leaked key means resetting it for everyone.
- Review is still manual: the reviewer reads the queue, edits, and adds pages to the public repository by hand.
- The sensitive-terms list is filled in by each person; the check cannot know a new project's name.
- Carried over from v0.2.11: `tra-dinh-muc-du-toan` has not been used to build a complete estimate; `thiet-ke-phong-nha` has not been run on a real floor plan; the Revit pyRevit tab has not been tried against a running Revit; the gateway (port 8764) does not start by itself after Windows restarts; the Windows installer is unsigned.
