# Hướng dẫn cài đặt trên máy mới: launcher và tri thức chung

Tài liệu này dành cho thành viên nhóm cài máy mới, và cho người quản lý dựng phần cổng nhận đề xuất. Áp dụng cho launcher **v0.2.12 trở lên**.

## 1. Tổng quan

```
Máy bạn (agent + launcher) ──đọc──▶ autocad-knowledge (công khai, trang đã duyệt)
        │
        └─ gửi đề xuất + khóa nhóm ─▶ Cổng Cloudflare ─▶ repo inbox (riêng tư) ─▶ người duyệt ─▶ autocad-knowledge
```

- **Đọc** tri thức chung không cần tài khoản nào: launcher tải thư mục `wiki/` của repo công khai về máy.
- **Gửi** đề xuất không cần tài khoản GitHub, chỉ cần **khóa nhóm** do người quản lý cấp. Đề xuất vào một hàng chờ riêng tư; chỉ khi người duyệt chấp nhận mới công khai.
- Thông tin riêng của dự án (số liệu, tên khách hàng, quyết định) **không** đi qua đường này.

| Vai trò | Làm phần |
|---|---|
| Thành viên | Mục 2 (cài máy), mục 3 (dùng hằng ngày) |
| Người quản lý và người duyệt | Mục 4 (dựng cổng, cấp khóa), mục 5 (duyệt) |

Địa chỉ đang dùng:

| Thành phần | Địa chỉ |
|---|---|
| Kho tri thức công khai | `https://github.com/KenjiIT/autocad-knowledge` |
| Cổng nhận đề xuất | `https://knowledge-gateway.kenjiit.workers.dev` |
| Hàng chờ (riêng tư) | `KenjiIT/common-knowledge-inbox` |

## 2. Cài máy mới (thành viên)

### 2.1 Yêu cầu
- Windows.
- Python 3.10 đến 3.13 có `tkinter` (bộ cài launcher cần). Lệnh `py -3` phải chạy được.
- AutoCAD (để làm việc với DWG); DXF offline không cần AutoCAD.
- Internet.
- Không cần Git hay tài khoản GitHub.

### 2.2 Cài launcher
1. Vào `https://github.com/KenjiIT/autocad-mcp-launcher/releases`, tải `AutoCAD-MCP-Launcher-Setup-0.2.12.exe` (hoặc bản mới hơn).
2. Mở file, chọn thư mục cài, hoàn tất. Lần đầu launcher tự cài thư viện cho hai MCP rồi mới hiện giao diện.
3. Bộ cài chưa có chữ ký, nên Windows có thể cảnh báo. Chọn **More info**, rồi **Run anyway**.
4. Tab **Điều khiển**, bấm **Bật kết nối cho agent**. Gateway chạy ở `http://127.0.0.1:8764`; kiểm tra bằng cách mở `http://127.0.0.1:8764/status` trong trình duyệt.

Sau khi nâng cấp từ bản cũ: **Thoát hẳn** launcher (chuột phải biểu tượng khay, chọn Thoát hẳn) rồi mở lại, để gateway nhận tool mới. Sau đó **mở phiên agent mới**: agent chỉ lấy danh sách tool một lần lúc kết nối, nên phiên đang mở vẫn dùng tool cũ.

### 2.3 Nối launcher với agent
Tab **Điều khiển**, chọn agent, bấm **Sao chép cấu hình**, làm theo gợi ý hiện ngay dưới ô:
- **Claude Code:** chạy lệnh được sao chép trong terminal của project.
- **Codex:** gộp vào `%USERPROFILE%\.codex\config.toml`.
- **Claude Desktop:** gộp vào `%APPDATA%\Claude\claude_desktop_config.json`, rồi thoát hẳn và mở lại.

### 2.4 Cài skill
**Cách 1: bằng launcher** (Claude Code, Codex). Tab **Cài đặt**, mục **Cài skill cho agent**: chọn agent và các skill, bấm cài. Cần có bốn skill tri thức: `knowledge-query`, `knowledge-capture`, `knowledge-promote`, `knowledge-lint`.

**Cách 2: Claude Desktop** (chỉ nhận file zip). Cài đặt, mục Skills, tải lên từng file zip trong thư mục `dist` của bản đã cài (cũng có trong `autocad-mcp-launcher-complete.zip` ở trang Releases, hoặc thư mục `dist` của repo): `knowledge-query.zip`, `knowledge-capture.zip`, `knowledge-promote.zip`, `knowledge-lint.zip`, cùng các skill AutoCAD bạn cần.

### 2.5 Tải tri thức chung
Tab **Cài đặt**, mục **Tri thức AutoCAD**, bấm **Tải tri thức**. Mặc định lưu ở `C:\Users\<tên bạn>\autocad-knowledge`; có thể **Đổi thư mục**. Làm lại bấm nút này mỗi khi muốn lấy bản mới.

Nút này chỉ tải về, không tải lên gì.

### 2.6 Nhập khóa nhóm để gửi đề xuất
1. Xin **khóa nhóm** từ người quản lý, qua kênh riêng (tin nhắn trực tiếp hoặc trình quản lý mật khẩu). Không gửi khóa qua email nhóm, ghi chú dùng chung hay vào repo.
2. Tab **Cài đặt**, mục **Gửi đề xuất tri thức**:
   - **Địa chỉ cổng:** đã điền sẵn `https://knowledge-gateway.kenjiit.workers.dev`. Địa chỉ phải bắt đầu bằng `https://`.
   - **Khóa nhóm:** dán khóa (ô ẩn ký tự).
3. Bấm **Lưu cấu hình gửi đề xuất**. Thấy "Đã lưu. Agent gửi được đề xuất." là xong.
4. Khóa nằm trong `launcher\state\settings.json` trên máy này. **Không** sao chép file này sang máy khác hay đưa vào repo.

Cách khác: đặt biến môi trường `KNOWLEDGE_TEAM_KEY` (và `KNOWLEDGE_GATEWAY_URL` nếu cần), ưu tiên hơn cài đặt trong ứng dụng.

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

### 2.8 Kiểm tra cài đặt xong
1. `http://127.0.0.1:8764/status` trả trạng thái JSON.
2. Trong agent, hỏi: "Liệt kê tool MCP bạn có." Phải thấy `knowledge` (đọc tri thức chung), `knowledge_propose` (gửi đề xuất), `skills`, `launcher_set_backend`.
3. Hỏi agent: "Tra tri thức chung về cách đọc mặt bằng kết cấu Revit." Nó phải gọi tool `knowledge` (hoặc skill `knowledge-query`) và nêu trang nó dựa vào. Tool `knowledge` đọc thư mục tri thức của launcher nên hoạt động cả khi agent không được cấp quyền vào thư mục đó; chưa tải tri thức thì nó báo `KNOWLEDGE_NOT_DOWNLOADED`.
4. Thử gửi (xem mục 3). Không chắc thì gửi một đề xuất thử và nhờ người quản lý xóa.

## 3. Dùng hằng ngày

| Bạn muốn | Nói với agent |
|---|---|
| Tra trước khi làm | "Tra kiến thức chung về ..." (hoặc agent tự gọi `knowledge-query`) |
| Ghi điều vừa học | "Ghi lại kiến thức này vào kho chung" |
| Chuyển từ ghi chú riêng của dự án | "Chuyển trang này thành tri thức chung" |
| Kiểm tra kho | "Lint kho tri thức chung" |

Luồng khi ghi: agent đối chiếu bản công khai (tránh trùng) → gỡ tên dự án và số liệu thật → viết vào `proposals/` → kiểm tra → **hỏi bạn có gửi không** → gọi `knowledge_propose`. Đọc lại bản nháp kỹ trước khi đồng ý, vì sau khi người duyệt chấp nhận trang sẽ **công khai**.

Kết quả gửi:

| Kết quả | Nghĩa | Việc cần làm |
|---|---|---|
| `ok: true` | Đã vào hàng chờ, chưa công khai | Chờ người duyệt |
| `NO_TEAM_KEY` | Chưa nhập khóa | Làm lại mục 2.6 |
| `REJECTED_LOCALLY` | Bị chặn trên máy (email, đường dẫn máy, thuật ngữ nhạy cảm, thiếu đầu trang...), **chưa gửi gì** | Sửa theo `issues` rồi gửi lại |
| 401 `Sai khóa nhóm` | Khóa sai hoặc đã được đổi | Hỏi người quản lý khóa mới |
| 422 | Cổng từ chối nội dung (có thể do thuật ngữ nhạy cảm của công ty) | Đọc `issues`, gỡ phần đó |
| 502 | Cổng không ghi được vào hàng chờ | Báo người quản lý (thường do khóa GitHub của cổng hết hạn) |
| Lỗi mạng | Không tới được cổng | Kiểm tra Internet; agent giữ trang trong `proposals/` để gửi lại sau |

## 4. Dựng cổng và cấp khóa (người quản lý)

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
5. Địa chỉ cổng wrangler in ra là địa chỉ để thành viên dùng ở mục 2.6. Nếu khác địa chỉ mặc định trong launcher, mỗi người cập nhật ô **Địa chỉ cổng**.
6. Kiểm tra: `curl https://<địa-chỉ-cổng>/health` trả `{"ok":true}`.

### 4.4 Cấp khóa cho thành viên
- Gửi `TEAM_KEY` riêng cho từng người qua kênh an toàn.
- **Khóa này dùng chung và nằm trên máy mỗi người**, nên không biết ai gửi (nhãn người gửi do người gửi tự khai) và ai có khóa cũng gửi được.
- Có người rời nhóm hoặc nghi lộ khóa: tạo khóa mới, `npx wrangler secret put TEAM_KEY`, phát khóa mới cho cả nhóm. Khóa cũ ngừng dùng được ngay.

### 4.5 Việc nên làm thêm
- **Giới hạn số đề xuất mỗi ngày:** `npx wrangler kv namespace create RATE`, dán `id` vào `wrangler.toml` (bỏ dấu `#` ba dòng `[[kv_namespaces]]`), rồi `npx wrangler deploy`. Mặc định 50 mỗi ngày (`DAILY_LIMIT`). Chưa làm thì ai có khóa cũng có thể làm đầy hàng chờ.
- Ghi ngày hết hạn của khóa GitHub vào lịch. Hết hạn thì cổng trả 502 cho mọi đề xuất.

## 5. Duyệt đề xuất (người duyệt)

Hiện làm thủ công. Cần quyền vào repo `common-knowledge-inbox` (riêng tư) và quyền ghi `autocad-knowledge`.

1. Xem hàng chờ: mở `proposals/` trong repo inbox trên GitHub, hoặc `gh api repos/KenjiIT/common-knowledge-inbox/contents/proposals --jq '.[].name'`.
2. Đọc từng trang. Kiểm tra:
   - Còn tên khách hàng, mã dự án, số liệu thật, tên người, đường dẫn máy? Có thì sửa hoặc từ chối.
   - Đã có trang tương tự trong `autocad-knowledge/wiki` chưa? Có thì gộp.
   - Nội dung có đúng không? Đối chiếu với bản vẽ hoặc tài liệu khi cần.
3. Chấp nhận: sửa đầu trang `status: confirmed`, điền `reviewed_by`, đặt tệp vào `wiki/<nhóm>/<slug>.md` của `autocad-knowledge`, thêm một dòng vào `wiki/index.md`, rồi commit và push. Có thể chạy `lint.py` của skill `knowledge-lint` (`py -3 <skill>\scripts\lint.py --root <thư mục chứa wiki>`) trước khi push.
4. Từ chối hoặc đã xử lý xong: xóa tệp khỏi `proposals/` của repo inbox, để hàng chờ chỉ còn việc chưa xử lý.
5. Thành viên bấm **Tải tri thức** để nhận trang mới.

Trang công khai sẽ **hiện với mọi người trên Internet** ngay khi push. Đọc kỹ trước khi đẩy.

## 6. Sự cố thường gặp

| Triệu chứng | Nguyên nhân | Cách sửa |
|---|---|---|
| Agent không thấy `knowledge` hoặc `knowledge_propose` | Gateway chạy bản cũ, hoặc phiên agent mở trước khi cập nhật | Thoát hẳn launcher, mở lại, **Bật kết nối cho agent**, rồi **mở phiên agent mới** |
| Mọi lệnh CAD báo `COM STA worker is poisoned` | Một lệnh COM chạy quá hạn (thường là đọc cả bản vẽ lớn) làm khóa kênh | Gọi `system init` (không đụng tới bản vẽ), hoặc khởi động lại MCP; với DWG lớn đọc từng layer |
| `drawing open` báo thành công nhưng tab không đổi (bản trước 0.2.13) | Lỗi cũ trên AutoCAD đầy đủ | Cập nhật lên 0.2.13 trở lên |
| `npx.ps1 cannot be loaded because running scripts is disabled` | PowerShell chặn script | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, mở lại PowerShell, hoặc dùng `npx.cmd` |
| Cổng báo lỗi chứng chỉ hoặc TLS ngay sau khi triển khai | Chứng chỉ subdomain mới chưa cấp xong | Chờ vài phút |
| wrangler: `Subdomain is unavailable` hoặc `is invalid` | Tên đã có người dùng, có chữ hoa, hoặc bạn nhập cả địa chỉ | Chỉ nhập **tên**, chữ thường, không `https://`, không `.workers.dev`. Tài khoản có thể đã có sẵn subdomain: xem ở Workers & Pages |
| `NO_TEAM_KEY` dù đã nhập | Chưa bấm Lưu, hoặc gateway chạy trước khi lưu | Bấm Lưu; thử gửi lại (gateway đọc khóa mỗi lần gửi) |
| Gửi bị chặn `REJECTED_LOCALLY` vì thuật ngữ nhạy cảm | Đúng như thiết kế | Gỡ thuật ngữ khỏi trang |
| Không gửi được vì cổng 401 | Khóa đã đổi | Xin khóa mới |
| Tải tri thức không được | Mất mạng, hoặc GitHub chặn | Thử lại; có thể đọc trực tiếp `https://raw.githubusercontent.com/KenjiIT/autocad-knowledge/main/wiki/index.md` |

## 7. Giới hạn đã biết
- Khóa nhóm dùng chung, nằm trên mỗi máy, không phải bí mật tuyệt đối.
- Chưa có giới hạn số đề xuất mỗi ngày cho tới khi gắn KV (mục 4.5).
- Duyệt thủ công; chưa có công cụ hỗ trợ.
- Kiểm tra nhạy cảm chỉ bắt mẫu đã biết (email, điện thoại, đường dẫn máy, khóa) và thuật ngữ bạn tự điền. Người duyệt là lớp cuối cùng.
- Bốn skill tri thức chưa được dùng trong một phiên làm việc thật với nhiều người.
- Chưa có tầng tri thức **riêng** theo dự án (SharePoint) ngoài tài liệu này; thông tin riêng của dự án vẫn lưu ở nơi riêng của dự án.
