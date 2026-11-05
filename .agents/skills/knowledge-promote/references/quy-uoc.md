# Quy ước thư mục tri thức chung

Tri thức chung là **công khai và không mật**. Bản công khai là repo `KenjiIT/autocad-knowledge`, launcher tải thư mục `wiki/` của nó về máy (nút **Tải tri thức**, mặc định `~/autocad-knowledge`). Không đưa vào đây: tên khách hàng, mã dự án và bản vẽ, địa chỉ lô đất, số liệu hợp đồng, tên người, đường dẫn máy cá nhân, khóa hay mật khẩu. Thông tin riêng của một dự án nằm ở nơi lưu riêng của dự án.

## Cấu trúc trong thư mục tri thức trên máy

```
wiki/                 trang đã duyệt, công khai (launcher ghi đè khi tải; đừng sửa trực tiếp)
  index.md            mục lục
  <nhóm>/<slug>.md
proposals/            trang đề xuất chờ duyệt (launcher không đụng tới)
sensitive-terms.local.txt   thuật ngữ nhạy cảm riêng của bạn (không đưa lên git)
```

Launcher chỉ ghi đè tệp trong `wiki/` khi tải và không xóa gì, nên `proposals/` và danh sách thuật ngữ an toàn.

## Mỗi trang một ý

Một trang trả lời một câu hỏi. Tên tệp là slug chữ thường, không dấu, nối bằng gạch ngang. Liên kết giữa trang dùng `[[slug]]`.

## Đầu trang của trang đề xuất

```yaml
---
title: Tên trang
type: concept        # concept | rule | howto | pitfall
topics: [cad, ket-cau]
status: draft
source: Mô tả nguồn (phiên làm việc, tài liệu, quy chuẩn), không nêu tên dự án
updated: 2026-11-05
reviewed_by:         # để trống; người duyệt điền
---
```

Các trang công khai hiện có chưa có đầu trang; thêm dần khi sửa trang. Khi trang đề xuất được duyệt, người duyệt đặt `status: confirmed`, điền `reviewed_by`, chuyển vào `wiki/<nhóm>/`, thêm một dòng vào `wiki/index.md` rồi đẩy lên repo công khai.

## Đường đi

1. **Đối chiếu bản công khai** (xem mục dưới) để không tạo trang trùng.
2. Ghi vào `proposals/` với `status: draft`.
3. Gỡ thông tin nhạy cảm, chạy `lint.py` (skill `knowledge-lint`).
4. Gửi đề xuất bằng tool `knowledge_propose` của launcher (cần khóa nhóm, nhập ở tab Cài đặt). Đề xuất vào hàng chờ riêng tư. Không có tool thì người dùng gửi tệp trong `proposals/` cho người duyệt. Người duyệt đọc, sửa, rồi đưa vào repo công khai.
5. Agent không tự sửa `wiki/` hay repo công khai.

## Đối chiếu với bản công khai

Bản trên máy có thể cũ. Trước khi tạo đề xuất:
- Đọc mục lục hiện hành: `https://raw.githubusercontent.com/KenjiIT/autocad-knowledge/main/wiki/index.md` (đọc được không cần đăng nhập), hoặc nhờ người dùng bấm **Tải tri thức**.
- Trang gần nghĩa đã có thì đọc nó, chỉ đề xuất phần **còn thiếu** hoặc bản sửa, và nói rõ đề xuất bổ sung cho trang nào.

## Việc cần gỡ trước khi đề xuất

| Gỡ | Thay bằng |
|---|---|
| Tên khách hàng, tên dự án, mã bản vẽ, mã lô | "một dự án căn hộ", "bản kiến trúc mẫu" |
| Số liệu thật (kích thước lô, diện tích, số căn) | Bỏ, hoặc khoảng chung ("gần 30 m") nếu số cần cho ý |
| Tên người, email, số điện thoại | Bỏ |
| Đường dẫn máy (`C:\Users\...`) | Mô tả vai trò ("thư mục làm việc") |
| Khóa, token, mật khẩu | Không bao giờ ghi |

Giữ lại: quy tắc, lý do, cách kiểm tra, tên công cụ, tên layer chuẩn, tên lệnh.
