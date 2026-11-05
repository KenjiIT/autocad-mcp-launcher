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

## Chạy thử trên máy (không cần tài khoản Cloudflare)

```
npm test
npx wrangler dev --local --var TEAM_KEY:khoa-thu --var GITHUB_TOKEN:khong-dung-that
```

`npm test` chạy 10 kiểm tra với GitHub giả. `wrangler dev` chạy cổng trong môi trường Cloudflare cục bộ; đã thử `/health` (200), sai khóa (401), thiếu đầu trang và chứa email (422). Bước ghi vào GitHub thật chưa được thử, vì cần khóa GitHub và repo inbox thật.

## Giới hạn cần biết

- **Khóa nhóm dùng chung.** Nằm trong cấu hình máy người dùng nên ai cài launcher đều đọc được. Chặn được người lạ ngẫu nhiên, không biết ai gửi (`sender` do người gửi tự khai). Khóa lộ thì đặt lại bằng `wrangler secret put TEAM_KEY` và phát cấu hình mới cho cả nhóm.
- **Người có khóa có thể làm đầy inbox bằng rác** (trong giới hạn kích thước và số lượng mỗi ngày). Họ không đụng được repo công khai, vì cổng chỉ ghi vào inbox.
- **Kiểm tra nhạy cảm chỉ bắt mẫu đã biết** và các thuật ngữ trong `SENSITIVE_TERMS`. Người duyệt vẫn phải đọc từng đề xuất trước khi công khai.
- Mẫu nhạy cảm trong `src/index.js` phải giữ đồng bộ với `PATTERNS` trong `.claude/skills/knowledge-lint/scripts/lint.py`.
- Khóa GitHub hết hạn thì cổng trả 502 cho mọi đề xuất hợp lệ.
