---
name: knowledge-capture
description: Ghi điều vừa học được sau một việc (cách đọc bản vẽ, lỗi công cụ và cách sửa, quy tắc thiết kế, quy trình) thành trang đề xuất cho tri thức chung công khai, đã gỡ thông tin dự án và đã đối chiếu bản công khai. Dùng khi người dùng nói 'ghi lại kiến thức', 'lưu kinh nghiệm này', 'đưa vào kho chung', 'đề xuất tri thức', hoặc khi gặp một trong các sự kiện đáng ghi (lỗi rồi tìm ra cách sửa, tool cư xử khác mô tả, người dùng chỉnh lại agent, phải thử nhiều cách mới ra, quy ước chưa ai ghi); khi đó tự ghi và gửi, báo người dùng sau.
---

# Ghi tri thức mới cho kho chung

Kết quả là **một tệp trong `proposals/`** của thư mục tri thức trên máy. Agent không sửa `wiki/` (launcher ghi đè khi tải) và không sửa repo công khai; người duyệt mới đưa trang vào. Quy ước, đầu trang, đường đi và bảng gỡ thông tin: [references/quy-uoc.md](references/quy-uoc.md). Đọc trước khi viết.

Thư mục tri thức: theo mục "Tìm thư mục tri thức" của skill `knowledge-query`. Chưa có thư mục thì hỏi người dùng nơi đặt; `proposals/` nằm cạnh `wiki/`.

## Khi nào cân nhắc (gắn với sự kiện, không chờ "cuối việc")

Agent không có tiến trình nền và không biết chắc việc đã xong, nên cân nhắc ngay khi một sự kiện sau xảy ra:

| Sự kiện | Vì sao đáng ghi |
|---|---|
| Một lỗi xảy ra, rồi bạn tìm ra cách khắc phục | Cặp "lỗi và cách sửa" là loại tri thức dùng lại nhiều nhất |
| Tool cư xử khác mô tả hoặc tài liệu (báo thành công nhưng kết quả không đúng) | Agent sau sẽ tin mô tả và lặp lại lỗi |
| Người dùng chỉnh lại bạn ("không phải thế, phải ...") | Là quy tắc do người có chuyên môn đưa ra |
| Bạn phải thử hai ba cách mới ra | Chi phí tìm kiếm đã bỏ ra, để người sau khỏi lặp lại |
| Bạn gặp một quy ước hay cấu trúc không có ghi ở đâu | Không có nguồn nào khác để tra |

Ba thời điểm: **ngay sau khi giải quyết xong** lỗi hoặc thắc mắc (còn nhớ nguyên nhân), **ngay sau khi người dùng chỉnh**, và **khi người dùng báo xong** hoặc trước báo cáo cuối (quét lại bảng trên). 
Ở mỗi điểm chỉ làm một việc nhỏ: tra `knowledge` xem đã có chưa, rồi nếu chưa thì ghi và gửi theo quy trình dưới, không cần hỏi trước. 
Công cụ cũng có thể nhắc bạn: một số lỗi (kênh COM bị khóa, `E_POSTCONDITION_MISMATCH`) trả kèm trường `hint` chỉ tới tri thức chung.

## Có đáng ghi không

Ghi khi cả ba đúng:
- **Không hiển nhiên:** phải mất công mới biết (lỗi lạ, hành vi công cụ, cách đọc khó).
- **Dùng lại được:** áp dụng cho dự án khác, không chỉ dự án này.
- **Chưa có sẵn** trong mã, tài liệu công cụ, `CAPABILITIES.md` hay bản công khai.

Không ghi: số liệu hay quyết định riêng của một dự án (để ở nơi lưu riêng của dự án), trạng thái công việc dở dang, điều suy đoán chưa kiểm chứng.

## Quy trình

1. **Đối chiếu bản công khai trước** (mục cuối của quy ước). Đọc mục lục hiện hành trên mạng, mở trang gần nghĩa. Đã có đủ thì dừng và nói với người dùng là không cần ghi. Có một phần thì chỉ đề xuất phần thiếu, ghi rõ bổ sung cho trang nào.
2. **Chọn loại:** `concept`, `rule`, `howto`, `pitfall`. Một trang một ý; lẫn hai chủ đề thì tách hai trang.
3. **Viết** vào `proposals/<slug>.md` theo đầu trang trong quy ước: `status: draft`, `reviewed_by` trống, `updated` là ngày hôm nay, `source` mô tả nguồn mà không nêu tên dự án. Ngắn, nêu **quy tắc và lý do**, kèm cách kiểm tra khi có.
4. **Gỡ thông tin dự án** theo bảng trong quy ước. Thay bằng ví dụ vô danh.
5. **Chạy lint** bằng skill `knowledge-lint` (`py -3 <skill>/scripts/lint.py --root <thư mục tri thức>`). Sửa đến khi hết lỗi, đặc biệt mục thuật ngữ nhạy cảm.
6. **Quyết định gửi.** Gửi ngay khi lint sạch và bạn chắc trang đã gỡ hết thông tin dự án. Còn nghi ngờ (lint còn lỗi, không chắc một chi tiết có nhạy cảm không, nội dung chưa kiểm chứng) thì **không gửi**: giữ ở `proposals/` và hỏi người dùng. Người duyệt vẫn đọc lại trước khi trang **công khai**.
7. **Gửi:** gọi tool `knowledge_propose` (launcher cung cấp) với `slug` là tên tệp bỏ đuôi `.md` và `content` là toàn bộ trang. Launcher kiểm tra lại trên máy rồi mới gửi tới hàng chờ duyệt. Kết quả `ok: true` nghĩa là đã vào hàng chờ, chưa công khai. Sau đó **báo người dùng một dòng**: tên tệp và trang nói gì.
   - `NO_TEAM_KEY`: chưa có khóa nhóm; bảo người dùng nhập ở tab Cài đặt của launcher, mục **Gửi đề xuất tri thức**.
   - `REJECTED_LOCALLY`: đọc `issues`, sửa trang rồi hỏi lại người dùng; chưa có gì rời khỏi máy.
   - Không có tool này hoặc cổng lỗi: giữ tệp trong `proposals/` và nhờ người dùng gửi tệp cho người duyệt.

## Lưu ý

- Chưa chắc một chi tiết là nhạy cảm hay không thì bỏ chi tiết đó, hoặc hỏi người dùng.
- Người dùng muốn giữ cho riêng dự án (hoặc đã dặn đừng gửi) thì không ghi ở đây; lưu vào nơi tri thức riêng của dự án.
- Không commit hay push repo công khai.
