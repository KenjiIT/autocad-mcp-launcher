# Cổng nhận đề xuất tri thức chung

Cloudflare Worker nhỏ. Máy người dùng gửi đề xuất (một trang markdown) kèm **khóa nhóm**; cổng kiểm tra rồi ghi vào repo **riêng tư** `KenjiIT/common-knowledge-inbox`. Người dùng không cần tài khoản GitHub, và khóa GitHub chỉ nằm trên Cloudflare, không nằm trên máy người dùng.

```
máy người dùng --POST /propose + X-Team-Key--> Worker --GitHub API--> repo inbox (riêng tư)
                                                                          |
                                                    người duyệt đọc, sửa, đưa vào autocad-knowledge (công khai)
```

## Cổng làm gì

- `POST /propose`, body JSON `{ "slug": "...", "content": "<markdown>", "sender": "tên máy hoặc người (tùy chọn)" }`, header `X-Team-Key`.
- Từ chối nếu: sai khóa (401), JSON hỏng hoặc slug sai (400), quá 50 KB (413), không đạt kiểm tra (422), hết số đề xuất trong ngày (429).
- Kiểm tra nội dung: có đầu trang đủ trường, `status: draft`, `reviewed_by` trống, không chứa email, số điện thoại, đường dẫn máy, khóa; không chứa thuật ngữ trong bí mật `SENSITIVE_TERMS`.
- `GET /health` trả `{"ok":true}`.

## Triển khai (một lần)

Cần: tài khoản Cloudflare (miễn phí, không cần thẻ), Node.js, và đã có repo `KenjiIT/common-knowledge-inbox`.

**1. Đăng ký Cloudflare.** Vào `dash.cloudflare.com`, đăng ký bằng email, xác nhận email. Vào **Workers & Pages**; lần đầu nó yêu cầu đặt tên miền con `tên-bạn.workers.dev`.

**2. Tạo khóa GitHub cho cổng** (github.com, Settings, Developer settings, Personal access tokens, **Fine-grained tokens**):
- Resource owner: `KenjiIT`. Repository access: **Only select repositories**, chọn **chỉ** `common-knowledge-inbox`.
- Permissions, Repository: **Contents: Read and write**. Không cấp quyền nào khác.
- Hạn: tối đa một năm. Ghi lại ngày hết hạn để thay khóa.
- Chép khóa ra (chỉ hiện một lần), đừng gửi vào chat.

**3. Đăng nhập và triển khai** (trong thư mục `knowledge-gateway`):

```
npx wrangler login
npx wrangler deploy
```

Lệnh `deploy` in ra địa chỉ dạng `https://knowledge-gateway.<tên-bạn>.workers.dev`.

**4. Đặt các bí mật** (mỗi lệnh sẽ hỏi giá trị, dán vào, không hiện ra màn hình):

```
npx wrangler secret put GITHUB_TOKEN
npx wrangler secret put TEAM_KEY
npx wrangler secret put SENSITIVE_TERMS
```

- `GITHUB_TOKEN`: khóa ở bước 2.
- `TEAM_KEY`: chuỗi ngẫu nhiên dài (ví dụ 32 ký tự). Tạo bằng: `py -3 -c "import secrets; print(secrets.token_urlsafe(24))"`.
- `SENSITIVE_TERMS`: các mã dự án, tên khách hàng, ngăn cách bằng dấu phẩy, ví dụ `MA-DU-AN-01,Ten Khach Hang`. Bí mật này không nằm trong mã nguồn công khai.

**5. (Tùy chọn) Giới hạn số đề xuất mỗi ngày.** Không có bước này thì cổng nhận không giới hạn ngày (vẫn có giới hạn kích thước):

```
npx wrangler kv namespace create RATE
```

Chép `id` in ra vào `wrangler.toml` (bỏ dấu `#` ở ba dòng `[[kv_namespaces]]`), rồi `npx wrangler deploy` lại. Mặc định 50 đề xuất mỗi ngày (`DAILY_LIMIT`).

**6. Thử:**

```
curl https://knowledge-gateway.<tên-bạn>.workers.dev/health
```

Thấy `{"ok":true}` là cổng chạy. Thử ghi thật cần một trang đề xuất hợp lệ và khóa nhóm; kết quả xuất hiện trong `proposals/` của repo inbox.

## Phát dữ liệu dự toán (dutoan.db) cho launcher

Cổng còn phát tệp `dutoan.db` (~106 MB) từ kho R2 riêng tư, để launcher tự tải và tự cập nhật. Tệp này chuyển từ phần mềm dự toán thương mại, **không được đưa lên chỗ công khai**.

```
launcher --GET /dutoan/manifest, /dutoan/db + X-Team-Key--> Worker --> R2 (bucket dutoan-data)
```

- `GET /dutoan/manifest` trả `{ sha256, size, version }`; `GET /dutoan/db` trả tệp. Cả hai cần khóa; sai khóa trả 401, chưa gắn kho 503, chưa tải lên 404.
- Launcher so SHA-256 trong manifest với tệp trên máy, chỉ tải khi khác, kiểm tra SHA-256 và đủ bảng rồi mới thay bản cũ.

**Dùng khóa riêng, không dùng khóa nhóm chung.** Khóa nhóm chung nằm sẵn trong launcher công khai (chỉ che mờ, không phải mã hóa), ai tải launcher cũng lấy ra được. Đặt `DUTOAN_KEY` thì chỉ khóa này mở được dữ liệu dự toán; không đặt thì cổng rơi về khóa nhóm chung (không khuyến nghị).

**Thiết lập (một lần, trong thư mục `knowledge-gateway`):**

```
npx wrangler r2 bucket create dutoan-data
```

Bỏ dấu `#` ở ba dòng `[[r2_buckets]]` trong `wrangler.toml`, rồi:

```
npx wrangler secret put DUTOAN_KEY
npx wrangler deploy
node tools/upload-dutoan.mjs "<đường-dẫn>/dutoan.db" "2026-11"
```

Khóa tạo bằng `py -3 -c "import secrets; print(secrets.token_urlsafe(24))"`. Đưa khóa cho từng người trong nhóm qua kênh riêng; họ dán vào launcher, tab Cài đặt, mục Dữ liệu dự toán, ô Khóa dữ liệu. R2 miễn phí 10 GB lưu trữ và không tính phí băng thông ra.

**Cập nhật dữ liệu:** chạy lại `node tools/upload-dutoan.mjs`. Launcher tự thấy bản mới khi mở (và sáu giờ một lần).

**Trước khi tải lên:** xóa dòng tài khoản `admin` còn sót trong DB, và xác nhận giấy phép dữ liệu GXD cho phép chia sẻ trong nhóm.

## Chạy thử trên máy (không cần tài khoản Cloudflare)

```
npm test
npx wrangler dev --local --var TEAM_KEY:khoa-thu --var GITHUB_TOKEN:khong-dung-that
```

`npm test` chạy 15 kiểm tra với GitHub giả. `wrangler dev` chạy cổng trong môi trường Cloudflare cục bộ; đã thử `/health` (200), sai khóa (401), thiếu đầu trang và chứa email (422). Bước ghi vào GitHub thật chưa được thử, vì cần khóa GitHub và repo inbox thật.

## Giới hạn cần biết

- **Khóa nhóm dùng chung.** Nằm trong cấu hình máy người dùng nên ai cài launcher đều đọc được. Chặn được người lạ ngẫu nhiên, không biết ai gửi (`sender` do người gửi tự khai). Khóa lộ thì đặt lại bằng `wrangler secret put TEAM_KEY` và phát cấu hình mới cho cả nhóm.
- **Người có khóa có thể làm đầy inbox bằng rác** (trong giới hạn kích thước và số lượng mỗi ngày). Họ không đụng được repo công khai, vì cổng chỉ ghi vào inbox.
- **Kiểm tra nhạy cảm chỉ bắt mẫu đã biết** và các thuật ngữ trong `SENSITIVE_TERMS`. Người duyệt vẫn phải đọc từng đề xuất trước khi công khai.
- Mẫu nhạy cảm trong `src/index.js` phải giữ đồng bộ với `PATTERNS` trong `.claude/skills/knowledge-lint/scripts/lint.py`.
- Khóa GitHub hết hạn thì cổng trả 502 cho mọi đề xuất hợp lệ.
