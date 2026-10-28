# AutoCAD MCP Launcher

Ứng dụng Windows chạy hai MCP server cho Codex, Claude Code, Claude Desktop hoặc Cursor. App khởi động mà không cần AutoCAD. Khi agent gọi tool, gateway ưu tiên AutoCAD và `autocad_beiming`; nếu AutoCAD không chạy, agent hỏi người dùng trước khi chuyển sang tạo DXF bằng `ezdxf`. Nếu agent gọi tool của `autocad_puran`, gateway ngắt MCP cũ trước khi mở MCP mới.

| MCP | Địa chỉ trong máy |
| --- | --- |
| Beiming custom MCP, derived from [beiming183-cloud/AutoCAD-MCP](https://github.com/beiming183-cloud/AutoCAD-MCP) | `http://127.0.0.1:8764/beiming/mcp` |
| [puran-water/autocad-mcp](https://github.com/puran-water/autocad-mcp) | `http://127.0.0.1:8764/puran/mcp` |

Puran được gắn dưới dạng Git submodule. Source Beiming đã được tách vào `autocad-beiming-mcp-custom` và tích hợp các tool sao chép theo lô, sao chép theo vùng giữa hai bản vẽ, và xóa theo lô. Skill đi kèm hướng dẫn agent nói rõ phương án trước khi sửa bản vẽ và đọc lại kết quả sau khi dùng tool. Skill là hướng dẫn cho agent; MCP mới là thành phần thao tác với AutoCAD.


## 1. Tải về

Cần Windows, Python 3.10–3.13 có `tkinter`, và Internet cho lần cài thư viện đầu tiên. DWG cần AutoCAD; DXF offline không cần AutoCAD. Repo GitHub này là **public**. Có thể tải gói cài đặt từ mục Releases mà không cần Git hoặc đăng nhập GitHub.

### Cài bằng bộ cài EXE

Trong mục Releases, tải `AutoCAD-MCP-Launcher-Setup-<phiên-bản>.exe` rồi mở file. Chọn thư mục cài đặt; shortcut Start Menu được tạo tự động. Có thể chọn thêm shortcut Desktop ở bước tác vụ bổ sung. Khi hoàn tất, bộ cài mở launcher; lần đầu chạy sẽ cài thư viện MCP rồi mới hiện ứng dụng. Cần cài sẵn Python 3.10–3.13 có `tkinter`.

### Máy không có Git

Mở [autocad-mcp-launcher-complete.zip](dist/autocad-mcp-launcher-complete.zip) trên GitHub, bấm **Download raw**, rồi giải nén. ZIP này chứa app, skill và mã nguồn của **cả hai MCP**. Mở thư mục `autocad-mcp-launcher` vừa giải nén và làm tiếp mục **2. Chạy app**. Máy dùng app không cần cài Git.

### Máy có Git

Mở PowerShell tại thư mục bạn muốn lưu app:

```powershell
git clone --recurse-submodules https://github.com/KenjiIT/autocad-mcp-launcher.git
cd autocad-mcp-launcher
```

Nếu đã clone mà thư mục Puran chưa có mã nguồn, chạy:

```powershell
git submodule update --init --recursive
```

**Không dùng nút Download ZIP của toàn bộ repo trên GitHub** nếu cần chạy Puran: ZIP đó không chứa mã nguồn trong submodule. Hãy dùng tệp **complete.zip** ở trên hoặc clone kèm `--recurse-submodules`.

## 2. Chạy app

1. Nhấp đúp `Start AutoCAD MCP.vbs` trong thư mục vừa clone hoặc giải nén. App mở mà không hiện cửa sổ CMD. Lần đầu, cửa sổ cài đặt chạy trước và cho biết tiến độ cài hai MCP. File `.cmd` vẫn có trong bộ cài để xem lỗi khởi động khi cần.
2. Bấm **Bật kết nối cho agent**. Gateway sẵn sàng ngay cả khi AutoCAD chưa chạy; các MCP tool vẫn hiện trong agent.
3. Khi làm việc, agent thử AutoCAD trước. Nếu AutoCAD không chạy, tool trả `AUTOCAD_UNAVAILABLE` và agent hỏi bạn có muốn xuất DXF thay thế không. Chỉ sau khi bạn đồng ý, agent gọi `launcher_set_backend` để dùng `ezdxf`. Agent cần gọi `drawing.save` để lưu DXF trước khi đổi MCP hoặc quay lại AutoCAD. Tệp `.dwg` chỉ dùng qua AutoCAD.
4. Thu nhỏ hoặc bấm X để đưa app xuống khay hệ thống; gateway vẫn chạy. Bấm biểu tượng khay hoặc nhấp đúp `Start AutoCAD MCP.vbs` để mở lại app đang chạy. Nhấp phải biểu tượng khay và chọn **Thoát hẳn** để dừng app cùng gateway.

Bạn có thể xem trạng thái gateway tại `http://127.0.0.1:8764/status`. Nhật ký nằm trong `launcher/logs/`. Khi làm việc với AutoCAD, app giữ AutoCAD mở lúc đổi MCP hoặc tắt gateway.

Với Beiming, launcher cho các thao tác đọc bản vẽ lớn (`drawing.audit`, `entity.collect`) tối đa **300 giây** thay vì 60 giây; File IPC cũng chờ tối đa 300 giây và gateway chờ phản hồi tối đa 360 giây. Các giới hạn này chỉ có hiệu lực sau khi thoát hẳn và mở lại app.

Beiming có thêm tool `copy_batching` để sao chép hàng loạt từ các handle gốc. Truyền `entity_ids` và `offsets` (`[dx, dy]`); tool tạo một bản sao cho mỗi cặp handle và độ dời, tối đa 100 bản sao/lần. Ví dụ, `entity_ids=["A1","A2"], offsets=[[100,0]]` sao chép hai đối tượng cùng độ dời; `entity_ids=["A1"], offsets=[[100,0],[200,0]]` sao chép một đối tượng đến hai vị trí. Kết quả trả handle từng bản sao. Mặc định nếu có lỗi, tool thử xóa các bản sao đã tạo và trả rõ các handle chưa xóa được; xem kết quả trước khi gọi lại.

Tool `copy_region_between_dwgs` chọn đối tượng trong một vùng chữ nhật của DWG nguồn và chép sang Model Space của DWG đích (tối đa 5.000 đối tượng mỗi lần). Mở cả hai DWG trong cùng một AutoCAD và kích hoạt DWG nguồn. Gọi `operation="preview"` với `source_path`, `target_path`, `corner1`, `corner2` và `selection_mode="window"` hoặc `"crossing"`; kết quả trả số lượng và `source_handles`. Sau khi xem danh sách, gọi `operation="copy"` với cùng vùng, `expected_handles` bằng `source_handles`, ngữ cảnh tài liệu nguồn hiện tại và `idempotency_key` duy nhất. `offset` là độ dời WCS tùy chọn. Đặt `save_target=true` nếu muốn lưu DWG đích ngay; mặc định chỉ sửa bản vẽ đang mở. Tool từ chối khi đơn vị `INSUNITS` hai bản vẽ khác nhau, trừ khi truyền `allow_unit_mismatch=true` sau khi đã kiểm tra tỷ lệ.

## 3. Thêm MCP vào agent

Trong app, chọn agent ở ô **Agent**, bấm **Sao chép cấu hình**, rồi làm theo mục tương ứng dưới đây. Địa chỉ `127.0.0.1` chỉ dùng được trên chính máy đang chạy app.

### Codex

Gộp hai mục dưới đây vào `%USERPROFILE%\.codex\config.toml`, rồi mở lại Codex:

```toml
[mcp_servers.autocad_beiming]
url = "http://127.0.0.1:8764/beiming/mcp"

[mcp_servers.autocad_puran]
url = "http://127.0.0.1:8764/puran/mcp"
```

Skill của dự án đã nằm tại `.codex/skills/autocad-agent-coordinator/SKILL.md`. Mở Codex từ thư mục project này để nó có thể tìm skill. MCP và skill được cài riêng: phải có cả hai nếu muốn agent dùng CAD và làm theo quy trình điều phối.

Trước khi dựng hoặc sửa bản vẽ từ hồ sơ đầu vào, coordinator sẽ gợi ý `autocad-verify-drawing-inputs` để kiểm tra nguồn, phiên bản, đơn vị, định vị và dữ liệu còn thiếu. Khi bắt đầu bản vẽ xây dựng 2D, coordinator tiếp tục gợi ý `autocad-start-construction-drawing`: tổ chức layer, hệ trục, hình học, chữ/kích thước và tờ in. Skill này tham khảo [hướng dẫn AutoCAD xây dựng của RDSIC](https://rdsic.edu.vn/hoc-thuat/autocad/huong-dan-su-dung-autocad-xay-dung-mot-cach-de-dang-va-hieu-qua-vi-cb.html) và dùng thông số thực tế của dự án thay cho các kích thước ví dụ trong bài. Nếu cần nhận diện ranh đất hoặc khối nhà trước khi vẽ, coordinator gợi ý `autocad-identify-and-measure`. Các skill đã có sẵn trong `.codex/skills/` và `.claude/skills/` của bản tải đầy đủ.

Với hồ sơ thiết kế xây dựng, `construction-document-router` xác định yêu cầu thuộc giai đoạn thiết kế, thi công hay hoàn công, sau đó kiểm tra tài liệu đầu vào còn thiếu. Hai skill `construction-design-stages` và `construction-drawing-records` hướng dẫn cụ thể thiết kế cơ sở, thiết kế kỹ thuật, thiết kế bản vẽ thi công, bản vẽ dùng trong thi công và cập nhật hiện trường. Giai đoạn hoàn công mới được nhận diện, chưa có quy trình xử lý. Các skill nằm trong `.codex/skills/` và `.claude/skills/`; skill điều phối AutoCAD vẫn áp dụng khi agent sửa bản vẽ qua MCP.

### Đọc bản vẽ và theo dõi thay đổi

Gọi `drawing` với `operation="audit"` để lấy tóm tắt bản vẽ; dùng `data={"include_entities":false}` nếu chưa cần danh sách đối tượng. `changed_only=true` trả các đối tượng thay đổi so với lần audit trước của cùng bản vẽ trong cùng tiến trình MCP và cùng phạm vi. Bỏ tùy chọn này nếu cần toàn bộ đối tượng. Khi chuyển sang bản vẽ khác, baseline được tách riêng; sau khi sửa, hãy đọc lại trước khi kết luận kết quả.


### Claude Code

Mở terminal trong project này và chạy:

```powershell
claude mcp add --transport http autocad_beiming http://127.0.0.1:8764/beiming/mcp
claude mcp add --transport http autocad_puran http://127.0.0.1:8764/puran/mcp
```

Mở lại phiên Claude Code. Skill đã nằm tại `.claude/skills/autocad-agent-coordinator/SKILL.md`; có thể yêu cầu rõ: `/autocad-agent-coordinator` trước một việc CAD.

### Claude Desktop Chat

Mở hoặc tạo `%APPDATA%\Claude\claude_desktop_config.json`. Trong app chọn **Claude Desktop** và sao chép JSON được tạo theo đường dẫn trên **máy của bạn**. Gộp hai mục vào `mcpServers` hiện có, giữ nguyên các MCP khác. Thoát hẳn Claude Desktop, kể cả biểu tượng khay hệ thống, rồi mở lại. Trong Chat, bấm **+ → Connectors** để kiểm tra hai server và tool.

Để thêm skill vào Claude Chat: Claude Desktop có kho skill riêng và chỉ nhận skill tải lên dạng zip, không đọc `~\.claude\skills`. Cách nhanh: mở app, tab **Cài đặt**, mục **Cài skill cho agent**, chọn **Claude Desktop (tải zip lên)**, chọn skill (bắt đầu bằng `autocad-agent-coordinator`) rồi bấm cài. App tạo các file zip trong `%USERPROFILE%\AutoCAD-MCP-Skills-Claude-Desktop` và mở thư mục đó. Trong Claude Desktop vào **Customize → Skills**, tải từng zip lên và bật. Có thể lấy sẵn các zip ở thư mục `dist/` (một file cho mỗi skill). Khi skill được cập nhật, tải lại zip tương ứng. Ngoài ra gateway có tool `skills` (chỉ đọc) và gửi lời nhắc khi kết nối: agent có thể tự đọc skill qua MCP mà không cần tải zip; mỗi skill cũng hiện thành một prompt trong menu của Claude Desktop. Việc tải skill không thay thế bước thêm MCP ở trên.

### Cursor

Gộp cấu hình này vào `%USERPROFILE%\.cursor\mcp.json`, rồi mở lại Cursor:

```json
{
  "mcpServers": {
    "autocad_beiming": { "url": "http://127.0.0.1:8764/beiming/mcp" },
    "autocad_puran": { "url": "http://127.0.0.1:8764/puran/mcp" }
  }
}
```

Skill trong repo hiện được đóng gói sẵn cho Codex, Claude Code và Claude Chat. Với Cursor, hãy đưa nội dung skill vào cơ chế hướng dẫn agent mà bạn đang dùng trong Cursor; chỉ thêm MCP sẽ không tự nạp skill.

### ChatGPT trên web

ChatGPT chạy trên cloud và không truy cập trực tiếp được `127.0.0.1` của máy bạn. Cần một endpoint HTTPS có xác thực và có thể truy cập từ Internet trước khi cấu hình MCP này trên ChatGPT web. App chưa tự tạo endpoint đó.

## 4. Dùng thử

Trong agent đã cấu hình, yêu cầu: “Kiểm tra bản vẽ AutoCAD đang mở, cho tôi biết tên bản vẽ và trạng thái kết nối. Chưa sửa gì.” Tool đọc trạng thái giúp xác nhận kết nối trước khi vẽ. Với yêu cầu thay đổi bản vẽ, skill sẽ hướng dẫn agent trình bày phương án bằng lời dễ hiểu trước khi gọi tool sửa, sau đó kiểm tra kết quả thực tế.

Nếu agent không hiện tool, kiểm tra theo thứ tự: app vẫn đang chạy; `/status` truy cập được; đã thêm cấu hình cho **đúng agent**; agent đã được khởi động lại; Claude Desktop đang ở **Chat**; và nhật ký trong `launcher/logs/` có lỗi hay không. Nếu app không mở khi nhấp `.vbs`, xem `launcher/logs/startup.log` hoặc mở `.cmd` để thấy lỗi. Nếu `autocad_beiming` không kết nối, kiểm tra AutoCAD đang mở với một bản vẽ và không có hộp thoại chặn thao tác.

## Giới hạn và nguồn

Gateway dùng backend `file_ipc` để làm việc với AutoCAD. App tạm thêm thư mục LISP vào `TRUSTEDPATHS` khi tải dispatcher rồi khôi phục giá trị cũ; `SECURELOAD` không bị tắt. Skill hướng dẫn agent nhưng chưa phải một cơ chế bắt buộc ở gateway: agent có thể gọi thẳng MCP tool nếu không nạp hoặc không làm theo skill.

### AutoCAD LT trên Windows

Beiming custom có adapter `lt-adapter/` cho AutoCAD LT 2024 trở lên. Khi chỉ LT đang mở, launcher tự chọn luồng `file_ipc_lt`; cũng có thể đặt `AUTOCAD_MCP_BACKEND=file_ipc_lt` để chọn rõ ràng. Mở một bản vẽ trong LT trước khi kết nối. Nếu có nhiều cửa sổ LT, đặt `AUTOCAD_MCP_ACAD_PID` theo PID cần dùng.

Trên LT, Python gửi lệnh qua cửa sổ AutoCAD và dispatcher AutoLISP, không gọi Python COM. Hãy thêm thư mục `autocad-beiming-mcp-custom/lisp-code` vào `TRUSTEDPATHS` của LT. Adapter đặt bản runtime của dispatcher upstream đã đổi tên hàm vào thư mục tin cậy đó, rồi nạp overlay từ `lt-adapter/lisp/mcp_dispatch_lt.lsp`; mã nguồn adapter vẫn nằm trong `lt-adapter/`. `drawing.context` trả `doc_id`, revision và lease token; lấy lại context khi chuyển bản vẽ.

Các đường riêng cho LT hiện gồm `entity.create_hatch` (polyline kín hoặc đường tròn), `delete_batching`, `block.define` (LINE, CIRCLE, ATTDEF), `copy_region_between_dwgs`, kiểm tra/tạo/chuyển/xóa layer, cập nhật system variable, đổi pattern hatch và tạo LINE từ JSON. Khi sao chép vùng, mở cả DWG nguồn và đích trong cùng một LT, kích hoạt nguồn, gọi `preview`, rồi dùng `source_handles` trả về để gọi `copy`. Các công cụ tạo hoặc sửa solid 3D không thuộc luồng LT này. DXF export, WBLOCK, quản lý nhiều document và các lệnh phụ thuộc giao diện trả `E_NOT_SUPPORTED_ON_LT`. Bốn luồng hatch, xóa theo lô, định nghĩa block và copy vùng đã được chạy trên AutoCAD LT 2027 với bản vẽ thử; không lưu các DWG thử.

Mã nguồn hai MCP thuộc các repo upstream được dẫn ở đầu trang và giữ nguyên lịch sử Git của họ. Launcher và skill của dự án này nằm trong repo chính.

Người duy trì repo có thể tạo lại ZIP đầy đủ bằng `python scripts/build_portable.py` sau khi cập nhật launcher hoặc submodule. ZIP loại bỏ `.git`, môi trường `.venv`, log và file output phát sinh.

## Cập nhật launcher

Launcher kiểm tra GitHub Release mới khi mở app. Nếu có bản mới, app hiển thị phiên bản và ghi chú phát hành để người dùng chọn cập nhật hoặc để sau. Gói tải về được đối chiếu SHA-256, app chờ yêu cầu AutoCAD đang chạy hoàn tất, tạm dừng MCP, cập nhật các file trong gói rồi mở lại launcher. Môi trường `.venv`, `launcher/logs`, thư mục output và file DWG cục bộ được giữ nguyên.

Tính năng này dùng GitHub Releases công khai. Để phát hành, cập nhật `VERSION` (ví dụ `0.2.0`), commit lên repo, sau đó đẩy tag tương ứng `v0.2.0`. GitHub Actions sẽ build `autocad-mcp-launcher-complete.zip`, tạo SHA-256 và đăng tải cả hai lên Release. Workflow nằm tại `.github/workflows/publish-release.yml`.
