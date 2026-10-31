---
name: autocad-apartment-floor-plan
description: Nghiệp vụ thiết kế mặt bằng chung cư - kết cấu và giao thông chung đi trước, chia căn bám cột vách, cửa, tường dày thật, diện tích thông thủy, thoát nạn, hộp kỹ thuật, báo cáo phương án. Dùng khi người dùng nói 'chung cư', 'căn hộ', 'mặt bằng điển hình', 'chia căn', 'phương án mặt bằng căn hộ', 'tầng điển hình', 'tháp rác', 'hộp kỹ thuật'. Dùng cùng autocad-start-construction-drawing, không thay thế nó.
---

# Mặt bằng chung cư

Đây là chung cư, không phải nhà trệt: **kết cấu, giao thông chung và kỹ thuật đi trước; chia phòng và nội thất đi sau.** Skill này chỉ chứa nghiệp vụ riêng của chung cư. Đơn vị, layer, chữ, kích thước, Layout và in thì theo [autocad-start-construction-drawing](../autocad-start-construction-drawing/SKILL.md).

Mọi con số (độ dày tường, kích thước cột/vách, khoảng hở cửa, diện tích tối thiểu, khoảng cách thoát nạn) lấy từ hồ sơ dự án hoặc quy chuẩn hiện hành. Chưa có thì hỏi người dùng; không tự đoán rồi im lặng.

## Trước khi bắt đầu

1. Có mặt bằng làm căn cứ thì làm Quy tắc 1 của `autocad-agent-coordinator` (xác định khu đất, chụp ảnh, người dùng xác nhận) trước khi lập kế hoạch.
2. Thiếu số liệu đầu vào thì hỏi một lần theo Quy tắc 2 của coordinator (bạn cung cấp, hoặc tôi vẽ theo giả định nêu rõ).
3. Làm trên bản sao hoặc layer phương án riêng; không vẽ đè lên bản gốc, không lưu hay ghi đè bản vẽ khi chưa hỏi.

## Quy trình

1. **Đọc kết cấu trước khi chia phòng.** Lấy lưới trục, cột, vách, lõi thang từ layer kết cấu (dùng [autocad-identify-and-measure](../autocad-identify-and-measure/SKILL.md)). Ghi vị trí và kích thước từng cột/vách, lưu bounding box để kiểm va chạm sau. Brief nói giữ lưới cột thì không đổi lưới.
2. **Chọn giải pháp kết cấu, không mặc định cột to.** Cân nhắc vách chịu lực (lõi thang, tường ngăn căn hộ, tường hành lang), cột dẹt hoặc cột vách giấu trong tường ngăn, cột chữ L/T ở góc. Cột tròn hoặc cột to chỉ khi có lý do (sảnh, thương mại dịch vụ, nhịp lớn). Nêu giải pháp đã chọn và lý do. Kích thước theo hồ sơ kết cấu hoặc hỏi người dùng.
3. **Giao thông chung và kỹ thuật.** Đặt lõi thang, hành lang, thoát nạn, hộp kỹ thuật (điện, nước, PCCC), tháp rác trước khi chia căn. Các số liệu thoát nạn và phòng cháy lấy từ quy chuẩn/hồ sơ; chưa có thì hỏi.
4. **Chia căn và phòng bám kết cấu.** Tường ngăn chạy qua hoặc ôm cột/vách. Cột nằm trong tường, ở góc phòng, hoặc giấu trong tủ/hộp kỹ thuật. Căn điển hình lặp lại thì dựng một căn rồi chép/lật theo [autocad-copy-similar-objects](../autocad-copy-similar-objects/SKILL.md).
5. **Cửa sau khi đã có cột, vách.** Kiểm từng cửa, kể cả cung cánh mở, với cột và vách.
6. **Tường có độ dày thật** (2 nét, hatch hoặc layer riêng), không vẽ tường 1 nét. Phân loại tường bao, tường ngăn căn hộ, tường ngăn phòng, vách kết cấu.
7. **Diện tích sau khi có tường dày.** Đo thông thủy (mép trong tường) và/hoặc tim tường tùy yêu cầu, ghi rõ dùng cách nào.
8. **Nội thất và thiết bị vệ sinh:** tra [autocad-block-library](../autocad-block-library/SKILL.md) trước khi vẽ tay.
9. **Rà soát theo [checklist](references/checklist.md) rồi mới giao.**

## Làm việc qua AutoCAD MCP

- Truy vấn entity trên layer cột/vách trước, lưu bounding box.
- Sau khi vẽ, kiểm va chạm: bounding box mỗi block cửa so với mỗi cột/vách; báo danh sách va chạm và sửa hết trước khi giao.
- Phát hiện nét trùng (cùng tọa độ đầu/cuối) và nét thừa bằng cách đọc entity; **báo danh sách và hỏi người dùng trước khi xóa**. Không chạy OVERKILL hay dọn hàng loạt khi chưa xác định phạm vi ảnh hưởng.
- Giới hạn của AutoCAD LT và quy ước màu: theo `autocad-agent-coordinator`.

## Báo cáo phương án

Dùng bảng ngắn:

| Mục | Nội dung |
|---|---|
| Giải pháp kết cấu | loại (vách, cột dẹt, cột L/T, cột to) và lý do |
| Độ dày tường | tường bao / ngăn căn hộ / ngăn phòng / vách, và nguồn số liệu |
| Cách tính diện tích | thông thủy hay tim tường |
| Bảng diện tích | từng phòng, từng căn, tổng so với tổng sàn |
| Checklist | mục đạt, mục chưa đạt, mục cần người dùng xác nhận |
