# Hướng dẫn cài đặt trên máy mới: launcher, tri thức chung và dữ liệu dự toán

Tài liệu này dành cho thành viên nhóm cài máy mới, và cho người quản lý dựng phần cổng nhận đề xuất và phát dữ liệu dự toán. Áp dụng cho launcher **v0.4.4 trở lên**. Riêng việc `dutoan` chạy **qua gateway HTTP** (mục 2.3, 2.8) và cổng buộc đọc skill (mục 3) có từ v0.4.4; các bản 0.4.0 đến 0.4.3 vẫn chạy `dutoan` kiểu stdio và không chặn tool CAD. Bản cũ hơn có chỗ khác; xem mục 8.

## 1. Tổng quan

```
Máy bạn (agent + launcher) ──đọc──▶ autocad-knowledge (công khai, trang đã duyệt)
        │
        ├─ gửi đề xuất (khóa nhóm đã nhúng sẵn) ─▶ Cổng Cloudflare ─▶ repo inbox (riêng tư) ─▶ người duyệt ─▶ autocad-knowledge
        │
        └─ nhập dutoan.db (từ tệp, hoặc tải từ cổng bằng khóa dữ liệu) ─▶ công cụ dutoan (đơn giá, định mức, dự toán)
```

- **Đọc** tri thức chung không cần tài khoản nào: launcher tải thư mục `wiki/` của repo công khai về máy.
- **Gửi** đề xuất không cần tài khoản GitHub và **không phải nhập khóa**: khóa nhóm đã được tích hợp sẵn trong bản phát hành chính thức. Đề xuất vào một hàng chờ riêng tư; chỉ khi người duyệt chấp nhận mới công khai.
- **Dữ liệu dự toán** (`dutoan.db`) **không đi kèm** launcher và không bao giờ được đưa lên chỗ công khai. Mỗi máy nhận tệp từ người quản lý (mục 2.8).
- Thông tin riêng của dự án (số liệu, tên khách hàng, quyết định) **không** đi qua đường gửi đề xuất.

Launcher phục vụ ba MCP cho agent, đều qua gateway HTTP: `autocad_beiming` (bản vẽ xây dựng), `autocad_puran` (bản vẽ MEP) và `dutoan` (đơn giá, định mức, dự toán).

| Vai trò | Làm phần |
|---|---|
| Thành viên | Mục 2 (cài máy), mục 3 (dùng hằng ngày) |
| Người quản lý và người duyệt | Mục 4 (dựng cổng, cấp khóa, phát dữ liệu dự toán), mục 5 (duyệt) |

Địa chỉ đang dùng:

| Thành phần | Địa chỉ |
|---|---|
| Trang tải launcher | `https://github.com/KenjiIT/autocad-mcp-launcher/releases` |
| Kho tri thức công khai | `https://github.com/KenjiIT/autocad-knowledge` |
| Cổng nhận đề xuất | `https://knowledge-gateway.kenjiit.workers.dev` |
| Hàng chờ (riêng tư) | `KenjiIT/common-knowledge-inbox` |

## 2. Cài máy mới (thành viên)

### 2.1 Yêu cầu
- Windows 64-bit. Không cần quyền quản trị.
- Python 3.10 đến 3.13 có `tkinter` (launcher cần). Lệnh `py -3` phải chạy được.
- AutoCAD để làm việc với DWG. DXF offline không cần AutoCAD.
- Internet (lần cài đầu tải thư viện cho ba MCP, và tải tri thức).
- Không cần Git hay tài khoản GitHub.

### 2.2 Cài launcher
1. Vào `https://github.com/KenjiIT/autocad-mcp-launcher/releases`, tải `AutoCAD-MCP-Launcher-Setup-<phiên-bản>.exe` của bản mới nhất (hiện là 0.4.4). Cạnh đó có tệp `.sha256` để đối chiếu nếu cần.
2. Mở file, chọn thư mục cài (mặc định `%LOCALAPPDATA%\Programs\AutoCAD MCP Launcher`), hoàn tất. Shortcut Start Menu được tạo tự động; shortcut Desktop là lựa chọn thêm.
3. Bộ cài chưa có chữ ký, nên Windows có thể cảnh báo. Chọn **More info**, rồi **Run anyway**.
4. Khi bộ cài mở launcher, **lần đầu** launcher tự cài thư viện cho ba MCP (`autocad_beiming`, `autocad_puran`, `dutoan`) rồi mới hiện giao diện. Cần mạng; môi trường `dutoan` thêm vài phút.
5. Tab **Điều khiển**, bấm **Bật kết nối cho agent**. Gateway chạy ở `http://127.0.0.1:8764`; kiểm tra bằng cách mở `http://127.0.0.1:8764/status` trong trình duyệt.

Tab **Cài đặt** có hai tùy chọn tiện: **Khởi động AutoCAD MCP Launcher cùng Windows** và **Tự bật MCP khi mở launcher** (không phải bấm Bật mỗi lần). AutoCAD vẫn chỉ được kết nối khi agent gọi tool.

Launcher chỉ chạy **một cửa sổ** cho mỗi thư mục cài: mở lần thứ hai chỉ gọi cửa sổ đang chạy hiện lên rồi tự thoát (từ v0.3.2).

Cách khác: tải `autocad-mcp-launcher-complete.zip` (gói di động, kèm `.sha256`) từ cùng trang Releases.

Sau khi nâng cấp từ bản cũ: **Thoát hẳn** launcher (chuột phải biểu tượng khay, chọn Thoát hẳn) rồi mở lại, để gateway nhận tool mới. Sau đó **mở phiên agent mới**: agent chỉ lấy danh sách tool và lời hướng dẫn một lần lúc kết nối, nên phiên đang mở vẫn dùng bản cũ.

### 2.3 Nối launcher với agent
Tab **Điều khiển**, chọn agent, bấm **Sao chép cấu hình**, làm theo gợi ý hiện ngay dưới ô. Cấu hình gồm các dòng `autocad_beiming`, `autocad_puran` và `dutoan`:
- **Claude Code:** chạy lệnh được sao chép trong terminal của project.
- **Codex:** gộp vào `%USERPROFILE%\.codex\config.toml`.
- **Claude Desktop:** gộp vào `%APPDATA%\Claude\claude_desktop_config.json`, rồi thoát hẳn và mở lại.

Cả ba MCP nay đều qua gateway HTTP (`http://127.0.0.1:8764/<tên>/mcp`), nên **launcher phải đang chạy và đã Bật kết nối cho agent** thì agent mới dùng được, kể cả `dutoan`. Khác với hai MCP AutoCAD (gateway chỉ chạy một MCP AutoCAD tại một thời điểm và cần AutoCAD), `dutoan` không dùng AutoCAD: gateway chạy riêng một tiến trình `dutoan` (môi trường `du-toan-mcp\.venv`, cổng nội bộ 8877) cho mọi agent, tự khởi động ở lần gọi đầu tiên.

**Đã cấu hình `dutoan` kiểu cũ (stdio, từ bản 0.4.0 đến 0.4.3)** thì phải đổi: Claude Code chạy `claude mcp remove dutoan` rồi thêm lại bằng lệnh mới; Codex xóa mục `command = ...` và thay bằng `url`; Claude Desktop thay mục `dutoan` bằng mục mới trong cấu hình sao chép. Sau đó thoát hẳn launcher, mở lại, và mở phiên agent mới.

### 2.4 Cài skill
**Cách 1: bằng launcher** (Claude Code, Codex). Tab **Cài đặt**, mục **Cài skill cho agent**: chọn agent và các skill (hoặc **Chọn tất cả**), bấm **Cài / cập nhật skill đã chọn**. Skill được chép vào thư mục dùng chung của tài khoản Windows. Nên có:
- bốn skill tri thức: `knowledge-query`, `knowledge-capture`, `knowledge-promote`, `knowledge-lint`;
- skill điều phối `autocad-agent-coordinator` và các skill AutoCAD bạn cần;
- `tra-dinh-muc-du-toan` nếu làm dự toán.

Khi cài cho Claude Code hoặc Codex, launcher còn ghi một **khối có đánh dấu** vào `~/.claude/CLAUDE.md` hoặc `~/.codex/AGENTS.md`, dặn agent nạp skill AutoCAD trước khi làm việc CAD, kể cả khi launcher đang tắt. Khối được cập nhật tại chỗ, không đụng phần bạn tự viết. Claude Desktop không có tệp chỉ dẫn toàn cục nên không được ghi.

**Cách 2: Claude Desktop** (chỉ nhận file zip). Cài đặt, mục Skills, tải lên từng file zip trong thư mục `dist` của bản đã cài (cũng có trong `autocad-mcp-launcher-complete.zip` ở trang Releases, hoặc thư mục `dist` của repo): `knowledge-query.zip`, `knowledge-capture.zip`, `knowledge-promote.zip`, `knowledge-lint.zip`, `autocad-agent-coordinator.zip`, cùng các skill AutoCAD và `tra-dinh-muc-du-toan.zip` nếu cần. Skill được cập nhật nội dung thì phải tải lại zip tương ứng.

### 2.5 Tải tri thức chung
Việc này **tự động**: khi mở launcher (và mỗi 24 giờ khi đang chạy) launcher hỏi GitHub bản phát hành mới nhất của `autocad-knowledge` (tag `vX.Y.Z`), tải về nếu mới hơn hoặc nếu máy chưa có, kiểm tra SHA-256, rồi thay các trang trong `wiki/`. Máy mới cài xong chỉ cần mở launcher là có tri thức.

Tab **Cài đặt**, mục **Tri thức AutoCAD**:
- Hộp **Tự kiểm tra và cập nhật tri thức mỗi 24 giờ** (mặc định bật). Dòng bên dưới cho biết đang giữ phiên bản nào và lần kiểm tra cuối.
- Nút **Tải tri thức** tải lại ngay, kể cả khi đã là bản mới nhất (để sửa khi lỡ xóa tệp).
- **Đổi thư mục…** nếu muốn lưu chỗ khác. Mặc định `C:\Users\<tên bạn>\autocad-knowledge`.

Launcher chỉ nhận **bản đã đóng tag**, không nhận mọi thay đổi trên nhánh `main`. Trang nào bản mới không còn sẽ bị xóa khỏi `wiki/`; `proposals/` và `sensitive-terms.local.txt` không bị đụng. Mất mạng hoặc GitHub không trả lời thì launcher im lặng thử lại sau và vẫn dùng bản đang có.

Nút này chỉ tải về, không tải lên gì.

### 2.6 Khóa nhóm để gửi đề xuất
Từ **v0.3.4**, khóa nhóm được **nhúng sẵn** trong bản phát hành chính thức (dựng từ bí mật của GitHub Actions, không nằm trong mã nguồn công khai). Tab **Cài đặt**, mục **Gửi đề xuất tri thức** hiện dòng "Khóa nhóm đã được tích hợp sẵn trong launcher; không cần nhập." Máy mới cài xong là agent gửi được, bạn không làm gì thêm.

Chỉ **bản tự dựng không có khóa** mới hiện thêm ô nhập: dán khóa nhóm do người quản lý cấp, bấm **Lưu cấu hình gửi đề xuất**, thấy "Đã lưu. Agent gửi được đề xuất." là xong. Khóa nhập tay nằm trong `launcher\state\settings.json`; không sao chép file này sang máy khác hay đưa vào repo. Địa chỉ cổng phải bắt đầu bằng `https://`.

Thứ tự dùng khóa: biến môi trường `KNOWLEDGE_TEAM_KEY` (và `KNOWLEDGE_GATEWAY_URL` nếu cần), rồi khóa nhập trong cài đặt, rồi khóa nhúng sẵn. Tool `knowledge_propose` không bao giờ trả khóa cho agent.

**Đây là che giấu, không phải bảo mật**: ai tải bản phát hành công khai cũng lấy lại được khóa. Khóa chỉ ngăn gửi bừa; chốt chặn thật là người duyệt và hàng chờ riêng tư.

### 2.7 Tạo danh sách thuật ngữ nhạy cảm (nên làm)
Đây là lớp chặn đầu tiên: trang chứa các thuật ngữ này sẽ không rời khỏi máy.

1. Mở thư mục tri thức (mặc định `C:\Users\<tên bạn>\autocad-knowledge`).
2. Tạo file `sensitive-terms.local.txt`, **mỗi dòng một thuật ngữ**: mã dự án, tên khách hàng, tên công trình, địa chỉ đặc trưng. Dòng bắt đầu bằng `#` là ghi chú. Ví dụ:

```
# mã dự án đang làm
MA-DU-AN-01
Tên Khách Hàng
```

3. Không tránh được hết, vì chỉ bắt được những gì bạn điền. Thêm mã mới mỗi khi nhận dự án mới.
4. File này **không bao giờ đưa lên mạng** và không nằm trong `wiki/` nên không bị ghi đè khi tải tri thức.

### 2.8 Nạp dữ liệu dự toán (`dutoan.db`)
Công cụ `dutoan` cần tệp `dutoan.db` (đơn giá, định mức, từ điển vật tư). Chưa có tệp thì trang chủ launcher báo chưa có dữ liệu và công cụ không tra được. Tệp này chuyển từ phần mềm dự toán thương mại, **không đưa lên chỗ công khai** và không chia sẻ ngoài nhóm khi chưa rõ giấy phép.

Tab **Cài đặt**, mục **Dữ liệu dự toán**. Khi nhập hoặc tải tệp mới, launcher tự nhờ gateway **thả tiến trình `dutoan`** (đang giữ tệp) và xóa các tệp phụ `-wal`/`-shm` của bản cũ rồi mới thay; tiến trình tự khởi động lại ở lần gọi kế tiếp. Chọn **một** cách:

1. **Nhập từ tệp… (đơn giản nhất, nên dùng).** Người quản lý gửi `dutoan.db` hoặc bản zip (bản 109 MB nén còn khoảng 18 MB). Bấm **Nhập từ tệp…**, chọn tệp. Launcher kiểm tra (kích thước, có đủ bảng `don_gia`, `dinh_muc`, `tu_dien_vat_tu`) rồi mới thay bản cũ; lỗi thì giữ nguyên bản đang dùng. Zip phải có đúng một tệp `.db` và không được giải nén quá 2 GB.
2. **Tự tải từ cổng nhóm.** Dán **Khóa dữ liệu** do người quản lý cấp (khóa riêng, không nhúng sẵn), bấm **Cập nhật từ cổng nhóm**. Hộp **Tự cập nhật dữ liệu dự toán từ cổng nhóm khi mở launcher** bật thì launcher hỏi cổng khi mở và sáu giờ một lần, chỉ tải khi SHA-256 khác bản trên máy.
3. **Tải theo địa chỉ.** Dán địa chỉ https tải trực tiếp (không cần đăng nhập) và SHA-256 (nên điền), bấm **Tải theo địa chỉ**. Link SharePoint thường là trang đăng nhập nên không dùng được.

Nút **Mở thư mục dữ liệu** mở chỗ lưu để chép tay. Mặc định tệp nằm ở `du-toan-mcp\data\dutoan.db` trong thư mục cài; biến môi trường `DUTOAN_DB_PATH` đổi chỗ này. Tệp chép tay vẫn được nhận.

Nếu vẫn báo tệp đang được dùng (ví dụ launcher đang chạy bản cũ chưa có gateway mới, hoặc một chương trình khác mở tệp), **thoát hẳn launcher**, đóng chương trình đang mở tệp (kể cả `dutoan` kiểu stdio còn sót trong phiên agent cũ) rồi nhập lại.

### 2.9 Thư viện block và AutoCAD LT (nếu dùng)
- Tab **Cài đặt**, mục **Thư viện block** có nút **Mở thư mục thư viện**: nơi lưu block dựng sẵn (nội thất, cây, thiết bị vệ sinh) dạng `.dwg` hoặc `.dxf`. Agent chèn bằng tên file; đơn vị mỗi file phải là mm. Quy ước đặt tên nằm trong `README.md` của thư mục.
- AutoCAD LT: LT gửi lệnh qua cửa sổ AutoCAD và dispatcher AutoLISP, nên phải thêm thư mục `autocad-beiming-mcp-custom\lisp-code` vào `TRUSTEDPATHS` của LT. Chi tiết ở `README.md` của repo, mục LT.

### 2.10 Kiểm tra cài đặt xong
1. `http://127.0.0.1:8764/status` trả trạng thái JSON. Trang chủ launcher hiện trạng thái `dutoan` (sẵn sàng hoặc chưa có dữ liệu).
2. Trong agent mới, hỏi: "Liệt kê tool MCP bạn có." Phải thấy `knowledge` (đọc tri thức chung), `knowledge_propose` (gửi đề xuất), `skills`, `launcher_set_backend`, các tool CAD của `autocad_beiming`/`autocad_puran`, và 12 tool của `dutoan` (`search_don_gia`, `phan_tich_don_gia`, `create_project`, `add_project_item`, `get_project_summary`, `search_vat_tu`, `calculate_cvc`, `lookup_svdt`, `calculate_svdt`, `compare_prices`, `get_thvt`, `list_projects`).
3. Hỏi agent: "Tra tri thức chung về cách đọc mặt bằng kết cấu Revit." Nó phải gọi tool `knowledge` (hoặc skill `knowledge-query`) và nêu trang nó dựa vào. Tool `knowledge` đọc thư mục tri thức của launcher nên hoạt động cả khi agent không được cấp quyền vào thư mục đó; chưa tải tri thức thì nó báo `KNOWLEDGE_NOT_DOWNLOADED`.
4. Nếu đã nạp dữ liệu dự toán: nhờ agent tra một đơn giá bằng `search_don_gia`; phải ra kết quả, không báo "Connection closed".
5. Thử gửi (xem mục 3). Không chắc thì gửi một đề xuất thử và nhờ người quản lý xóa.

## 3. Dùng hằng ngày

| Bạn muốn | Nói với agent |
|---|---|
| Làm việc với bản vẽ AutoCAD | Cứ nêu việc (vẽ, đo, kiểm tra, bóc khối lượng). Agent nạp skill `autocad-agent-coordinator` trước, rồi các skill chuyên biệt; việc mơ hồ thì nó hỏi lại một lần |
| Tra trước khi làm | "Tra kiến thức chung về ..." (hoặc agent tự gọi `knowledge-query`) |
| Tra đơn giá, định mức, lập dự toán | "Tra đơn giá ...", "Phân tích đơn giá mã ...", "Tạo dự toán cho ..." (agent dùng tool `dutoan` và skill `tra-dinh-muc-du-toan`) |
| Ghi điều vừa học | "Ghi lại kiến thức này vào kho chung" |
| Chuyển từ ghi chú riêng của dự án | "Chuyển trang này thành tri thức chung" |
| Kiểm tra kho | "Lint kho tri thức chung" |

**Gateway buộc agent đọc skill trước khi dùng tool CAD.** Ở lệnh CAD đầu tiên của mỗi phiên, nếu agent chưa đọc skill `autocad-agent-coordinator` qua tool `skills`, gateway trả lỗi `SKILL_NOT_READ` kèm đúng việc cần làm; agent đọc skill rồi gọi lại là chạy. Không cần bạn làm gì. Chỉ việc đọc thân skill điều phối bằng tool `skills` được tính. Các tool `skills`, `knowledge`, `knowledge_propose`, `launcher_set_backend` và `dutoan` không bị chặn. Tắt/bật ở tab **Cài đặt**, ô "Buộc agent đọc skill điều phối trước khi dùng tool CAD" (có hiệu lực ngay, mặc định bật). Áp dụng từ v0.4.4.

**Agent tự ghi và gửi, không hỏi trước.** Lời dặn này nằm trong hướng dẫn mà launcher gửi cho mọi agent khi kết nối (từ v0.3.5), nên áp dụng ở mọi dự án và mọi máy. Khi có lỗi mà tìm ra cách sửa, tool cư xử khác mô tả, bạn chỉnh lại agent, hoặc gặp quy ước chưa ai ghi: agent đối chiếu bản công khai (tránh trùng) → gỡ tên dự án, tên khách hàng, mã dự án, số liệu thật, đường dẫn máy → viết vào `proposals/` → kiểm tra (lint) → gọi `knowledge_propose` → báo bạn **một dòng**. Lint còn lỗi hoặc còn nghi ngờ một chi tiết nhạy cảm thì agent **không gửi**, giữ lại và hỏi bạn. Bạn dặn đừng gửi thì không gửi. Đây là lời dặn cho mô hình, không có gì ép buộc; chỗ chặn thật là người duyệt, nên đọc kỹ từng trang trong hàng chờ trước khi đóng tag, vì trang được duyệt sẽ **công khai**.

Kết quả gửi:

| Kết quả | Nghĩa | Việc cần làm |
|---|---|---|
| `ok: true` | Đã vào hàng chờ, chưa công khai | Chờ người duyệt |
| `NO_TEAM_KEY` | Không có khóa nào (thường chỉ gặp ở bản tự dựng) | Làm theo mục 2.6; bản chính thức thì cài lại bản mới nhất |
| `REJECTED_LOCALLY` | Bị chặn trên máy (email, đường dẫn máy, thuật ngữ nhạy cảm, thiếu đầu trang...), **chưa gửi gì** | Sửa theo `issues` rồi gửi lại |
| 401 `Sai khóa nhóm` | Khóa nhúng sẵn đã bị đổi ở cổng | Cập nhật launcher lên bản mới nhất (mục 4.4) |
| 422 | Cổng từ chối nội dung (có thể do thuật ngữ nhạy cảm của công ty) | Đọc `issues`, gỡ phần đó |
| 502 | Cổng không ghi được vào hàng chờ | Báo người quản lý (thường do khóa GitHub của cổng hết hạn) |
| Lỗi mạng | Không tới được cổng | Kiểm tra Internet; agent giữ trang trong `proposals/` để gửi lại sau |

## 4. Dựng cổng, cấp khóa và phát dữ liệu dự toán (người quản lý)

Làm một lần cho cả nhóm. Chi tiết từng lệnh nằm trong `knowledge-gateway/README.md` của repo launcher (thư mục này có trong repo, **không** có trong bộ cài, nên người quản lý cần tải repo hoặc xem trên GitHub); dưới đây là trình tự.

### 4.1 Hai repo GitHub
- `autocad-knowledge`: **công khai**, chỉ chứa trang đã duyệt trong `wiki/`.
- `common-knowledge-inbox`: **riêng tư**, chứa `proposals/` và chỉ người duyệt vào được.

### 4.2 Khóa GitHub cho cổng
GitHub, Settings, Developer settings, Fine-grained tokens, tạo khóa:
- Chỉ repo `common-knowledge-inbox`.
- Chỉ quyền **Contents: Read and write**.
- Hạn tối đa một năm; ghi lại ngày hết hạn để thay.
- Chép khóa ngay (chỉ hiện một lần).

### 4.3 Cloudflare
1. Đăng ký tại `dash.cloudflare.com` (miễn phí, không cần thẻ). Trong **Compute, Workers & Pages** đặt hoặc kiểm tra subdomain `workers.dev` (chỉ chữ thường, số, gạch ngang).
2. Mở PowerShell trong thư mục `knowledge-gateway` và chạy:

```
npx wrangler login
npx wrangler deploy
npx wrangler secret put GITHUB_TOKEN
npx wrangler secret put TEAM_KEY
npx wrangler secret put SENSITIVE_TERMS
```

   Nếu PowerShell chặn `npx.ps1`, chạy một lần `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` hoặc gõ `npx.cmd` thay `npx`.

3. Ba bí mật:
   - `GITHUB_TOKEN`: khóa ở bước 4.2.
   - `TEAM_KEY`: chuỗi ngẫu nhiên dài, tạo bằng `py -3 -c "import secrets; print(secrets.token_urlsafe(24))"`.
   - `SENSITIVE_TERMS`: mọi mã dự án và tên khách hàng, ngăn cách bằng dấu phẩy, ví dụ `MA-DU-AN-01,Ten Khach Hang`.
4. Giá trị chỉ nhập vào ô hỏi của wrangler, **không dán vào chat, tài liệu hay file trong repo**.
5. Địa chỉ cổng mặc định của launcher là hằng `DEFAULT_GATEWAY_URL` trong `launcher/knowledge_propose.py`. Địa chỉ wrangler in ra khác giá trị đó thì sửa hằng này rồi phát hành bản mới. Cách tạm: mỗi người sửa ô **Địa chỉ cổng** (tab Cài đặt, mục Gửi đề xuất tri thức, ô này luôn hiện và sửa được) rồi bấm **Lưu cấu hình gửi đề xuất**.
6. Kiểm tra: `curl https://<địa-chỉ-cổng>/health` trả `{"ok":true}`.

### 4.4 Khóa nhóm: nhúng vào bản phát hành, không phát tay
- Khóa nhúng vào gói lúc dựng bản phát hành: đặt **cùng giá trị** `TEAM_KEY` vào bí mật `KNOWLEDGE_TEAM_KEY` của repo launcher (GitHub, Settings, Secrets and variables, Actions). Workflow `Build launcher release` chạy `scripts/write_team_key.py` để tạo `launcher/team_key.dat` (mã hóa nhẹ, che chứ không bảo mật). Thành viên cài bản phát hành là gửi được, **không ai phải nhập khóa**.
- **Khóa dùng chung và nằm trên máy mỗi người**, nên cổng không biết ai gửi (nhãn người gửi do người gửi tự khai) và ai tải được launcher công khai cũng lấy lại được khóa.
- **Đổi khóa** (nghi lộ, hoặc có người rời nhóm): `npx wrangler secret put TEAM_KEY`, cập nhật bí mật `KNOWLEDGE_TEAM_KEY`, rồi đóng tag bản launcher mới. Từ lúc đổi, các launcher đã phát hành **không gửi được** (401) cho tới khi người dùng cập nhật lên bản mới.
- Bản tự dựng không có `team_key.dat` thì hiện ô nhập khóa; gửi khóa cho người đó riêng qua kênh an toàn.

### 4.5 Phát dữ liệu dự toán
Tệp `dutoan.db` được chuyển từ phần mềm dự toán thương mại (GXD); **chưa kiểm tra giấy phép** có cho phép chia sẻ trong nhóm hay không. Không đưa lên kho công khai.

1. **Làm bản sạch trước khi gửi:** xóa tài khoản `admin` (mật khẩu băm của bản web cũ) khỏi tệp, rồi tạo bản mới bằng `VACUUM INTO`. Không gửi tệp đang dùng, vì vùng trống của SQLite còn giữ chuỗi băm.
2. **Cách đơn giản:** nén zip bản sạch (109 MB còn khoảng 18 MB), gửi riêng cho từng thành viên; họ bấm **Nhập từ tệp…** (mục 2.8).
3. **Cách tự động qua cổng (không bắt buộc):** bật R2, tạo bucket `dutoan-data`, đặt bí mật `DUTOAN_KEY`, triển khai lại cổng, rồi `node tools/upload-dutoan.mjs <dutoan.db>`. Các bước ở `knowledge-gateway/README.md`. Phát **Khóa dữ liệu** (`DUTOAN_KEY`) riêng cho từng thành viên.
   - **Phải đặt `DUTOAN_KEY` riêng.** Không đặt thì cổng rơi về khóa nhóm chung, mà khóa này nằm sẵn trong launcher công khai, nên ai tải launcher cũng lấy được dữ liệu.
   - Cập nhật dữ liệu: chạy lại `upload-dutoan.mjs`; launcher tự thấy bản mới khi mở và sáu giờ một lần.

### 4.6 Việc nên làm thêm
- **Giới hạn số đề xuất mỗi ngày:** `npx wrangler kv namespace create RATE`, dán `id` vào `wrangler.toml` (bỏ dấu `#` ba dòng `[[kv_namespaces]]`), rồi `npx wrangler deploy`. Mặc định 50 mỗi ngày (`DAILY_LIMIT`). Chưa làm thì ai có khóa cũng có thể làm đầy hàng chờ, và nay agent tự gửi nên hàng chờ dễ đầy hơn.
- Ghi ngày hết hạn của khóa GitHub vào lịch. Hết hạn thì cổng trả 502 cho mọi đề xuất.
- Phát hành launcher: chỉ đẩy tag `vX.Y.Z` khớp tệp `VERSION`; workflow tự dựng gói, bộ cài `.exe`, `.sha256` và tạo Release (đừng tạo Release thủ công: thiếu tệp đính kèm thì launcher không cập nhật được).

## 5. Duyệt đề xuất (người duyệt)

Hiện làm thủ công. Cần quyền vào repo `common-knowledge-inbox` (riêng tư) và quyền ghi `autocad-knowledge`. **Agent tự gửi không hỏi trước**, nên bước đọc kỹ dưới đây là lớp chặn thật.

1. Xem hàng chờ: mở `proposals/` trong repo inbox trên GitHub, hoặc `gh api repos/KenjiIT/common-knowledge-inbox/contents/proposals --jq '.[].name'`.
2. Đọc từng trang. Kiểm tra:
   - Còn tên khách hàng, mã dự án, số liệu thật, tên người, đường dẫn máy? Có thì sửa hoặc từ chối.
   - Đã có trang tương tự trong `autocad-knowledge/wiki` chưa? Có thì gộp.
   - Nội dung có đúng không? Đối chiếu với bản vẽ hoặc tài liệu khi cần.
3. Chấp nhận: sửa đầu trang `status: confirmed`, điền `reviewed_by`, đặt tệp vào `wiki/<nhóm>/<slug>.md` của `autocad-knowledge`, thêm một dòng vào `wiki/index.md`, rồi commit và push. Có thể chạy `lint.py` của skill `knowledge-lint` (`py -3 <skill>\scripts\lint.py --root <thư mục chứa wiki>`) trước khi push.
4. Từ chối hoặc đã xử lý xong: xóa tệp khỏi `proposals/` của repo inbox, để hàng chờ chỉ còn việc chưa xử lý.
5. **Đóng tag để phát hành.** Chỉ đẩy tag, workflow của `autocad-knowledge` tự kiểm tra (`lint.py`), dựng gói `autocad-knowledge-wiki.zip` kèm SHA-256 và tạo Release (đừng tạo Release thủ công: thiếu tệp đính kèm thì launcher không cập nhật được):

   ```
   git tag v0.2.0
   git push origin v0.2.0
   ```

   Tăng số giữa khi thêm hoặc sửa trang đáng kể, số cuối khi sửa nhỏ. Nên đặt bí mật `SENSITIVE_TERMS` của repo (Settings, Secrets and variables, Actions) để bước kiểm tra chặn được mã dự án và tên khách hàng.
6. Mọi launcher tự nhận bản mới trong vòng 24 giờ (hoặc người dùng bấm **Tải tri thức**).

Trang đã đẩy lên `main` **chưa** tới người dùng cho tới khi đóng tag, nên bước 5 là cổng phát hành cuối cùng. Trang công khai **hiện với mọi người trên Internet** ngay khi push lên `main`; đọc kỹ trước khi đẩy.

## 6. Sự cố thường gặp

| Triệu chứng | Nguyên nhân | Cách sửa |
|---|---|---|
| Windows cảnh báo khi mở bộ cài | Bộ cài chưa có chữ ký | More info, rồi Run anyway |
| Lần mở đầu launcher chạy rất lâu | Đang cài thư viện cho ba MCP, gồm môi trường `dutoan` | Chờ vài phút, cần mạng. Lỗi thì xem thư mục `launcher\logs\` trong thư mục cài (ví dụ `gateway.log`, và `<tên-mcp>-install.log` của từng MCP) |
| Gateway thoát ngay khi bấm Bật kết nối | Một MCP không khởi động được | Mở `launcher\logs\gateway.log` và log của MCP được nhắc tên trong thông báo lỗi |
| Có nhiều cửa sổ launcher cùng lúc (bản trước 0.3.2) | Lỗi cũ về khóa tiến trình | Tắt hết (Thoát hẳn từ khay, hoặc Task Manager nếu còn `pythonw.exe`), cập nhật lên 0.3.2 trở lên |
| Agent không thấy `knowledge`, `knowledge_propose` hoặc `dutoan` | Gateway chạy bản cũ, hoặc phiên agent mở trước khi cập nhật | Thoát hẳn launcher, mở lại, **Bật kết nối cho agent**, rồi **mở phiên agent mới** |
| `dutoan` báo "Connection closed" (bản trước 0.4.0) | Thư viện `mcp` bản 2 đổi API | Cập nhật lên 0.4.0 trở lên (đã ghim `mcp<2`) |
| `dutoan` chạy nhưng không tra được | Chưa có `dutoan.db` | Làm mục 2.8; trang chủ launcher phải hiện "Sẵn sàng" |
| Nhập dữ liệu báo tệp đang bị giữ | Gateway cũ chưa có đường thả `dutoan`, `dutoan` kiểu stdio còn chạy trong một phiên agent cũ, hoặc chương trình khác đang mở tệp | Thoát hẳn launcher và mở lại (bản mới), đóng các phiên agent cũ, nhập lại |
| `dutoan` không kết nối sau khi cập nhật launcher | Agent vẫn cấu hình `dutoan` kiểu stdio cũ | Cấu hình lại bằng địa chỉ `http://127.0.0.1:8764/dutoan/mcp` (mục 2.3), mở phiên agent mới |
| Tool CAD trả `SKILL_NOT_READ` | Phiên chưa đọc skill `autocad-agent-coordinator` (hoặc gateway vừa khởi động lại, hoặc đây là phiên mới) | Bình thường: agent gọi `skills` với `operation=get`, `name=autocad-agent-coordinator` rồi gọi lại. Lỗi lặp lại dù đã đọc: agent chưa dùng tool `skills` (đọc tệp bằng công cụ khác không tính), hoặc máy khách không giữ mã phiên; thử mở phiên mới, hoặc tắt ô chặn ở tab Cài đặt |
| `dutoan` trả lỗi 503 | Thiếu môi trường `du-toan-mcp\.venv`, hoặc cổng nội bộ 8877 bị chiếm, hoặc tiến trình thoát khi khởi động | Mở `launcher\logs\dutoan.log`; mở app để cài lại thư viện; đóng chương trình đang dùng cổng 8877 |
| Nhập dữ liệu báo thiếu bảng hoặc sai kích thước | Tệp hỏng hoặc không phải `dutoan.db` | Xin lại tệp; bản đang dùng không bị đổi |
| Tải dữ liệu theo địa chỉ không được | Link là trang đăng nhập (SharePoint) | Dùng link tải trực tiếp, hoặc **Nhập từ tệp…** |
| Cập nhật dữ liệu từ cổng báo chưa có khóa | Chưa dán **Khóa dữ liệu** | Xin khóa từ người quản lý, hoặc dùng **Nhập từ tệp…** |
| Mọi lệnh CAD báo `COM STA worker is poisoned` | Một lệnh COM chạy quá hạn (thường là đọc cả bản vẽ lớn) làm khóa kênh | Gọi `system init` (không đụng tới bản vẽ), hoặc khởi động lại MCP; với DWG lớn đọc từng layer |
| `drawing open` báo thành công nhưng tab không đổi (bản trước 0.2.13) | Lỗi cũ trên AutoCAD đầy đủ | Cập nhật lên 0.2.13 trở lên |
| Agent không tự ghi tri thức | Phiên mở trước khi cập nhật (lời dặn chỉ nhận lúc kết nối), hoặc agent bận việc khác | Mở phiên agent mới; không có gì ép buộc, có thể nhắc "ghi lại kiến thức này" |
| `npx.ps1 cannot be loaded because running scripts is disabled` | PowerShell chặn script | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, mở lại PowerShell, hoặc dùng `npx.cmd` |
| Cổng báo lỗi chứng chỉ hoặc TLS ngay sau khi triển khai | Chứng chỉ subdomain mới chưa cấp xong | Chờ vài phút |
| wrangler: `Subdomain is unavailable` hoặc `is invalid` | Tên đã có người dùng, có chữ hoa, hoặc bạn nhập cả địa chỉ | Chỉ nhập **tên**, chữ thường, không `https://`, không `.workers.dev`. Tài khoản có thể đã có sẵn subdomain: xem ở Workers & Pages |
| `NO_TEAM_KEY` | Bản tự dựng chưa nhập khóa | Nhập khóa (mục 2.6) và bấm Lưu; bản chính thức thì cài lại bản mới nhất |
| Gửi bị chặn `REJECTED_LOCALLY` vì thuật ngữ nhạy cảm | Đúng như thiết kế | Gỡ thuật ngữ khỏi trang |
| Không gửi được vì cổng 401 | Khóa ở cổng đã đổi so với khóa nhúng trong launcher | Cập nhật launcher lên bản mới nhất |
| Tải tri thức không được | Mất mạng, GitHub chặn, hoặc chưa có bản phát hành nào được đóng tag | Xem dòng trạng thái dưới nút; thử lại sau. Chưa có tag thì người duyệt phải đóng tag đầu tiên (mục 5) |
| Dòng trạng thái báo SHA-256 không khớp | Gói tải về bị hỏng hoặc bị can thiệp | Không dùng; bấm Tải tri thức thử lại, nếu vẫn báo thì báo người duyệt |

## 7. Giới hạn đã biết
- Khóa nhóm nhúng sẵn chỉ là che giấu, không phải bảo mật; ai tải launcher công khai cũng lấy lại được.
- Lời dặn agent tự ghi và gửi là hướng dẫn cho mô hình, không có gì ép buộc; chưa kiểm chứng đầy đủ trong nhiều phiên thật.
- Gateway chỉ buộc **một bước**: đọc skill `autocad-agent-coordinator` trước khi dùng tool CAD. Nó không kiểm được agent có làm theo skill, hay có nạp thêm các skill chuyên biệt khớp yêu cầu hay không. Mới thử với client MCP của Python; Claude Code, Codex và Claude Desktop thật chưa thử (chúng cần gửi lại `Mcp-Session-Id`, nếu không thì dùng chung cửa sổ 30 phút).
- Chưa có giới hạn số đề xuất mỗi ngày cho tới khi gắn KV (mục 4.6), trong khi agent tự gửi.
- Duyệt thủ công; chưa có công cụ hỗ trợ.
- Kiểm tra nhạy cảm chỉ bắt mẫu đã biết (email, điện thoại, đường dẫn máy, khóa) và thuật ngữ bạn tự điền. Người duyệt là lớp cuối cùng.
- `dutoan.db` chuyển từ phần mềm thương mại; giấy phép chia sẻ trong nhóm chưa được kiểm tra. Kết quả tra chưa được đối chiếu độ chính xác với phần mềm gốc, và chưa thử đủ 12 tool.
- Theo ghi chú phát hành, chưa thử các việc sau trong cửa sổ launcher thật hoặc trên máy thứ hai: bộ cài đóng gói của các bản gần đây, nút **Nhập từ tệp…** và **Cập nhật từ cổng nhóm** bấm trong giao diện, việc ghi khối chỉ dẫn khi cài skill, cổng dữ liệu dự toán với Cloudflare thật.
- Chưa có tầng tri thức **riêng** theo dự án (SharePoint) ngoài tài liệu này; thông tin riêng của dự án vẫn lưu ở nơi riêng của dự án.

## 8. Khác biệt so với hướng dẫn cũ (launcher trước 0.4.2)
- **Trước 0.2.14:** tri thức tải từ `main` khi bấm nút, chưa tự cập nhật theo tag.
- **Trước 0.3.2:** có thể mở nhiều cửa sổ launcher cùng lúc.
- **Trước 0.3.4:** phải nhập khóa nhóm thủ công ở tab Cài đặt (mục 2.6 cũ).
- **Trước 0.3.5:** lời dặn agent tự ghi tri thức chỉ có trong `AGENTS.md` của repo launcher, không tới agent ở dự án khác.
- **Trước 0.4.0:** không có MCP `dutoan` và mục Dữ liệu dự toán.
- **Trước 0.4.1:** không tự tải dữ liệu dự toán từ cổng, và cài skill chưa ghi khối chỉ dẫn vào `CLAUDE.md`/`AGENTS.md`.
- **Trước 0.4.2:** chưa có nút **Nhập từ tệp…**.
- **0.4.3:** gỡ hai tab Revit thử nghiệm khỏi launcher (không ảnh hưởng cài đặt, tri thức hay dữ liệu dự toán).
- **Từ 0.4.4:** gateway chặn tool CAD (`SKILL_NOT_READ`) cho tới khi phiên đã đọc skill điều phối; `dutoan` chạy qua gateway HTTP (`/dutoan/mcp`) thay vì stdio; cấu hình agent đổi sang `url`, và launcher tự thả tiến trình `dutoan` trước khi thay `dutoan.db`.
