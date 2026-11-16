---
name: autocad-apartment-floor-plan
description: Nghiệp vụ thiết kế mặt bằng chung cư - kết cấu và giao thông chung đi trước, dừng ở từng cổng để dựng phương án cho người dùng chọn (chỉ tiêu, hình khối, lõi và hành lang, căn điển hình), chia căn bám cột vách, cửa, tường dày thật, diện tích thông thủy, thoát nạn theo QCVN 06, hiệu quả diện tích NFA/GFA, hộp kỹ thuật, báo cáo phương án, nhật ký quyết định. Dùng khi người dùng nói 'chung cư', 'căn hộ', 'mặt bằng điển hình', 'chia căn', 'phương án mặt bằng căn hộ', 'tầng điển hình', 'lõi thang', 'hình khối', 'tháp rác', 'hộp kỹ thuật'. Dùng cùng autocad-start-construction-drawing, không thay thế nó.
---

# Mặt bằng chung cư

Đây là chung cư, không phải nhà trệt: **kết cấu, giao thông chung và kỹ thuật đi trước; chia phòng và nội thất đi sau.** Skill này chỉ chứa nghiệp vụ riêng của chung cư. Đơn vị, layer, chữ, kích thước, Layout và in thì theo [autocad-start-construction-drawing](../autocad-start-construction-drawing/SKILL.md).

Mọi con số (độ dày tường, kích thước cột/vách, khoảng hở cửa, diện tích tối thiểu, khoảng cách thoát nạn) lấy từ hồ sơ dự án hoặc quy chuẩn hiện hành. Chưa có thì hỏi người dùng; không tự đoán rồi im lặng. Quy chuẩn PCCC và nhà chung cư: [qcvn-06-chung-cu.md](references/qcvn-06-chung-cu.md). Hiệu quả diện tích và dạng mặt bằng: [hieu-qua-dien-tich.md](references/hieu-qua-dien-tich.md).

## Dừng ở từng cổng để người dùng chọn

Các quyết định lớn nối tiếp nhau và quyết định sau bị quyết định trước ràng buộc, nên **không vẽ một mạch đến cuối**. Ở mỗi cổng, agent dựng 2 đến 3 phương án dựa trên chỉ tiêu, đo chỉ số, nêu khuyến nghị, hỏi người dùng bằng `AskUserQuestion`, chờ lựa chọn rồi mới đi tiếp. Chi tiết, mẫu bảng so sánh, nhật ký quyết định và cách học từ lựa chọn: [cong-duyet-phuong-an.md](references/cong-duyet-phuong-an.md).

| Cổng | Người dùng quyết định |
|---|---|
| 1. Chỉ tiêu | Xác nhận số liệu đầu vào và giả định |
| 2. Hình khối | Dạng hình khối, hình dạng sàn tầng điển hình |
| 3. Lõi và hành lang | Vị trí lõi, kiểu hành lang, số căn mỗi tầng |
| 4. Căn điển hình | Cách bố trí bên trong căn |
| 5. Giao | Nhận bản vẽ hoặc yêu cầu sửa |

Quy tắc chung:
- Mỗi phương án nằm trên layer riêng; không vẽ đè bản gốc. Phương án không được chọn giữ lại (tắt hiển thị) đến khi bàn giao.
- Chỉ số đo từ bản vẽ phương án, không lấy số tham khảo thay cho kết quả đo.
- Phương án vi phạm quy chuẩn thì nêu rõ điều vi phạm, không giấu và không tự chỉnh số cho vừa.
- Cổng sau phát hiện quyết định trước không đạt thì dừng, báo con số, đề xuất quay lại cổng trước và hỏi. Không lặng lẽ sửa quyết định đã duyệt.
- Người dùng nói bỏ qua cổng thì chỉ trình ở cổng 5 và ghi việc đó vào nhật ký quyết định.

## Trước khi bắt đầu

1. Có mặt bằng làm căn cứ thì làm Quy tắc 1 của `autocad-agent-coordinator` (xác định khu đất, chụp ảnh, người dùng xác nhận) trước khi lập kế hoạch.
2. Thiếu số liệu đầu vào thì hỏi một lần theo Quy tắc 2 của coordinator (bạn cung cấp, hoặc tôi vẽ theo giả định nêu rõ).
3. Làm trên bản sao hoặc layer phương án riêng; không vẽ đè lên bản gốc, không lưu hay ghi đè bản vẽ khi chưa hỏi.
4. Hỏi người dùng nơi đặt **nhật ký quyết định** của dự án (một lần), vì sau mỗi cổng phải ghi vào đó.

## Quy trình

1. **Chốt chỉ tiêu (Cổng 1).** Lập bảng khu đất, mật độ, hệ số sử dụng, số tầng và tầng hầm, tổng sàn, cơ cấu căn, chiều cao PCCC, hướng. Mỗi dòng ghi nguồn: người dùng cấp, đọc từ bản vẽ, hay giả định. Người dùng xác nhận rồi mới đi tiếp.
2. **Đọc kết cấu trước khi chia phòng.** Lấy lưới trục, cột, vách, lõi thang từ layer kết cấu (dùng [autocad-identify-and-measure](../autocad-identify-and-measure/SKILL.md)). Ghi vị trí và kích thước từng cột/vách, lưu bounding box để kiểm va chạm sau. Brief nói giữ lưới cột thì không đổi lưới. Chưa có kết cấu (đang ở giai đoạn ý tưởng) thì bỏ qua bước này và ghi rõ.
3. **Phương án hình khối (Cổng 2).** Dựng 2 đến 3 dạng khác nhau rõ rệt (tấm, tháp lõi giữa, nhiều cánh) cho tầng điển hình, đo diện tích sàn, số căn ước tính, số mặt thoáng, hướng. Người dùng chọn.
4. **Chọn giải pháp kết cấu, không mặc định cột to.** Cân nhắc vách chịu lực (lõi thang, tường ngăn căn hộ, tường hành lang), cột dẹt hoặc cột vách giấu trong tường ngăn, cột chữ L/T ở góc. Cột tròn hoặc cột to chỉ khi có lý do (sảnh, thương mại dịch vụ, nhịp lớn). Nêu giải pháp đã chọn và lý do. Kích thước theo hồ sơ kết cấu hoặc hỏi người dùng.
5. **Phương án lõi và hành lang (Cổng 3).** Dựng 2 đến 3 phương án vị trí lõi thang, hộp kỹ thuật, tháp rác và kiểu hành lang. Đo NFA/GFA, tỷ lệ lõi, khoảng cách thoát nạn xa nhất, chiều dài khoang hành lang; kiểm theo [qcvn-06-chung-cu.md](references/qcvn-06-chung-cu.md). Người dùng chọn.
6. **Chia căn và phòng bám kết cấu, bắt đầu bằng căn điển hình (Cổng 4).** Dựng 2 phương án bố trí cho mỗi loại căn chính; người dùng chọn. Tường ngăn chạy qua hoặc ôm cột/vách. Cột nằm trong tường, ở góc phòng, hoặc giấu trong tủ/hộp kỹ thuật. Căn đã duyệt lặp lại thì chép/lật theo [autocad-copy-similar-objects](../autocad-copy-similar-objects/SKILL.md).
7. **Cửa sau khi đã có cột, vách.** Kiểm từng cửa, kể cả cung cánh mở, với cột và vách.
8. **Tường có độ dày thật** (2 nét, hatch hoặc layer riêng), không vẽ tường 1 nét. Phân loại tường bao, tường ngăn căn hộ, tường ngăn phòng, vách kết cấu.
9. **Diện tích sau khi có tường dày.** Đo thông thủy (mép trong tường) và/hoặc tim tường tùy yêu cầu, ghi rõ dùng cách nào. Tính lại NFA/GFA của phương án đã chọn và so với con số ở cổng 3.
10. **Nội thất và thiết bị vệ sinh:** tra [autocad-block-library](../autocad-block-library/SKILL.md) trước khi vẽ tay.
11. **Rà soát theo [checklist](references/checklist.md) rồi trình ở Cổng 5.**
12. **Ghi nhật ký quyết định** sau mỗi cổng, và cân nhắc ghi tri thức chung theo [cong-duyet-phuong-an.md](references/cong-duyet-phuong-an.md) mục "Học".

## Làm việc qua AutoCAD MCP

- Truy vấn entity trên layer cột/vách trước, lưu bounding box.
- Sau khi vẽ, kiểm va chạm: bounding box mỗi block cửa so với mỗi cột/vách; báo danh sách va chạm và sửa hết trước khi giao.
- Phát hiện nét trùng (cùng tọa độ đầu/cuối) và nét thừa bằng cách đọc entity; **báo danh sách và hỏi người dùng trước khi xóa**. Không chạy OVERKILL hay dọn hàng loạt khi chưa xác định phạm vi ảnh hưởng.
- Giới hạn của AutoCAD LT và quy ước màu: theo `autocad-agent-coordinator`.

## Báo cáo phương án

Dùng bảng ngắn:

| Mục | Nội dung |
|---|---|
| Quyết định đã duyệt | từng cổng: phương án người dùng chọn và chỉ số chính |
| Giải pháp kết cấu | loại (vách, cột dẹt, cột L/T, cột to) và lý do |
| Độ dày tường | tường bao / ngăn căn hộ / ngăn phòng / vách, và nguồn số liệu |
| Cách tính diện tích | thông thủy hay tim tường |
| Bảng diện tích | từng phòng, từng căn, tổng so với tổng sàn |
| Hiệu quả diện tích | NFA/GFA, tỷ lệ lõi, cách đo |
| Quy chuẩn | mục đã đối chiếu, mục chưa kiểm được |
| Checklist | mục đạt, mục chưa đạt, mục cần người dùng xác nhận |
