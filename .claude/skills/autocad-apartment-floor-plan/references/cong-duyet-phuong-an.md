# Cổng duyệt phương án

Mặt bằng chung cư có nhiều quyết định nối tiếp nhau, quyết định sau bị quyết định trước ràng buộc. Vì vậy **agent dừng ở từng cổng, dựng phương án, để người dùng chọn, rồi mới đi tiếp.** Không tự chọn thay người dùng, không vẽ một mạch đến cuối rồi mới trình.

Người dùng nói "đi tiếp không cần dừng" thì bỏ qua các cổng 2 đến 4 và chỉ trình ở cổng 5. Ghi việc đó vào nhật ký quyết định.

## Các cổng

| Cổng | Dừng ở đâu | Người dùng quyết định |
|---|---|---|
| 1. Chỉ tiêu | Trước khi dựng bất cứ phương án nào | Xác nhận số liệu đầu vào và đâu là giả định |
| 2. Hình khối tầng điển hình | Sau khi có chỉ tiêu | Dạng hình khối và hình dạng sàn |
| 3. Lõi và hành lang | Sau khi chọn hình khối | Vị trí lõi, kiểu hành lang, số căn mỗi tầng |
| 4. Căn điển hình | Sau khi chọn lõi và hành lang | Cách bố trí bên trong một căn |
| 5. Giao | Sau cửa, tường dày, diện tích, nội thất, checklist | Nhận bản vẽ hoặc yêu cầu sửa |

### Cổng 1: chỉ tiêu
Lập bảng và hỏi người dùng xác nhận. Mỗi dòng ghi rõ nguồn: **người dùng cấp**, **đọc từ bản vẽ** hoặc **giả định của agent**.

- Khu đất đã xác nhận (Quy tắc 1 của `autocad-agent-coordinator`), diện tích, ranh, lùi.
- Chỉ tiêu quy hoạch: mật độ xây dựng, hệ số sử dụng đất, chiều cao hoặc số tầng, số tầng hầm. Lấy từ hồ sơ quy hoạch của dự án hoặc hỏi người dùng; QCVN 01 chưa xác minh trong skill này nên không tự điền số (xem [qcvn-06-chung-cu.md](qcvn-06-chung-cu.md), mục "Khung pháp lý").
- Tổng diện tích sàn, diện tích sàn tầng điển hình (nếu đã biết).
- Cơ cấu căn: tỷ lệ studio, 1, 2, 3 phòng ngủ và diện tích mục tiêu mỗi loại.
- Chiều cao PCCC của nhà (quyết định nhóm yêu cầu trong [qcvn-06-chung-cu.md](qcvn-06-chung-cu.md)).
- Hướng, tầm nhìn quan trọng, khu vực ồn.

Còn dòng nào là giả định thì hỏi theo "Cách hỏi" của coordinator: người dùng cung cấp, hoặc agent vẽ theo giả định nêu rõ.

### Cổng 2: hình khối
Dựng 2 đến 3 phương án khác nhau ở **một trục rõ ràng** (ví dụ tấm dài, tháp lõi giữa, chữ L), không phải 3 biến thể gần giống nhau. Chọn các dạng phù hợp chỉ tiêu, bảng dạng ở [hieu-qua-dien-tich.md](hieu-qua-dien-tich.md).

Chỉ số mỗi phương án: diện tích sàn tầng, số căn ước tính, tỷ lệ cạnh dài/ngắn, số mặt thoáng trung bình mỗi căn, hướng căn xấu nhất.

### Cổng 3: lõi và hành lang
Dựng 2 đến 3 phương án về vị trí lõi (giữa, đầu, hai lõi) và kiểu hành lang (một bên, hai bên). Kiểm theo [qcvn-06-chung-cu.md](qcvn-06-chung-cu.md) trước khi trình; phương án vi phạm thì nêu rõ điều vi phạm chứ không giấu.

Chỉ số mỗi phương án (đo từ bản vẽ phương án, cách đo ở [hieu-qua-dien-tich.md](hieu-qua-dien-tich.md)):

| Chỉ số | Ghi |
|---|---|
| NFA/GFA | diện tích bán hoặc sử dụng chia diện tích sàn |
| Tỷ lệ lõi | lõi chia diện tích sàn |
| Số căn mỗi tầng và số căn một mặt thoáng | |
| Khoảng cách xa nhất tới thang thoát nạn | so với quy chuẩn |
| Chiều dài khoang hành lang | so với quy chuẩn |
| Số thang bộ thoát nạn, số thang máy | |
| Căn bị hướng xấu hoặc không thông gió xuyên phòng | |
| Lưới cột tầng điển hình so với bãi xe tầng hầm | Thực hành phổ biến là lưới cột chung giữa hầm và tầng ở, nên cột lệch lưới thì ảnh hưởng chỗ đỗ xe hoặc phải chuyển tải. Chưa có nguồn xác nhận trong skill này; chưa có hồ sơ hầm thì hỏi người dùng, đừng tự đoán |

### Cổng 4: căn điển hình
Mỗi loại căn chính dựng 2 phương án bố trí (khu ướt gom về đâu, ban công hoặc logia, lối vào, thông gió). Chỉ số: diện tích thông thủy, số phòng, phòng ngủ có cửa ra ngoài, khu ướt bám hộp kỹ thuật hay không.

### Cổng 5: giao
Sau khi làm cửa, tường dày, diện tích, nội thất và rà checklist, trình bản vẽ kèm bảng "Báo cáo phương án" trong `SKILL.md` và danh sách mục cần xác nhận.

## Cách trình mỗi cổng

1. Mỗi phương án vẽ trên **layer phương án riêng** (ví dụ `PA-A`, `PA-B`, `PA-C`), không vẽ đè bản gốc. Bật từng layer, chụp ảnh. Không có kết nối AutoCAD thì trình bằng hình vẽ chữ hoặc sơ đồ, nêu rõ.
2. Đưa **một bảng so sánh** chỉ số, rồi nêu **phương án khuyến nghị và lý do**, kèm điểm yếu của nó. Khuyến nghị chỉ là gợi ý.
3. Hỏi bằng công cụ hỏi có lựa chọn (`AskUserQuestion`), mỗi lựa chọn ghi sẵn chỉ số chính trong phần mô tả, vì người dùng có thể chỉ thấy hộp thoại. Luôn có chỗ cho "phương án khác" hoặc "kết hợp".
4. Chờ trả lời. Không dựng cổng kế tiếp khi chưa có lựa chọn.
5. Phương án người dùng không chọn **giữ lại** trên layer của nó (tắt hiển thị) cho đến khi bàn giao, để quay lại được.

Số phương án: tối thiểu 2, tối đa 3. Nếu chỉ tiêu chỉ cho phép đúng một phương án hợp lệ, nói thẳng và nêu lý do thay vì bịa thêm.

## Quay lại khi không đạt
Nếu ở cổng sau phát hiện quyết định trước làm không đạt (ví dụ lõi đã chọn khiến khoang hành lang quá dài), **dừng, báo con số vi phạm, đề xuất quay lại cổng trước** và hỏi. Không lặng lẽ sửa quyết định đã duyệt.

## Nhật ký quyết định và học từ lựa chọn

Mục đích: để lần sau agent đề xuất sát hơn, không phải để chọn thay người dùng.

### Ghi mỗi quyết định
Sau mỗi cổng ghi một mục vào **nhật ký quyết định riêng của dự án**. Lần đầu hỏi người dùng đặt ở đâu; repo có nơi tri thức riêng cho dự án (ví dụ thư mục wiki cục bộ) thì đề xuất nơi đó. Không ghi vào kho tri thức chung ở bước này vì có số liệu dự án.

```
## <ngày> | Cổng <số> | <tên quyết định>
- Phương án và chỉ số chính: A (...), B (...), C (...)
- Agent khuyến nghị: <phương án> vì <lý do>
- Người dùng chọn: <phương án>
- Lý do người dùng nêu: <nguyên văn, nếu có; không có thì ghi "không nêu">
- Phân tích của agent (giả thuyết, chưa xác nhận): <vì sao có thể chọn như vậy, dựa trên chỉ số nào>
- Khác khuyến nghị: có/không
```

### Khi người dùng chọn khác khuyến nghị
Hỏi **một câu ngắn** vì sao (cho phép bỏ qua). Đây là lúc học được nhiều nhất. Đừng tranh luận lại lựa chọn.

### Học
- Phân tích của agent luôn gắn nhãn **giả thuyết**. Một lựa chọn chưa phải quy luật.
- Chỉ nâng thành **ưu tiên của người dùng** khi cùng một khuynh hướng lặp lại từ hai lần trở lên, hoặc người dùng tự nói rõ. Ghi ưu tiên ở đầu nhật ký, kèm các mục làm bằng chứng.
- Ưu tiên chỉ dùng để **xếp thứ tự và chọn khuyến nghị**. Vẫn phải dựng đủ phương án khác biệt, không thu hẹp lựa chọn chỉ vì "người dùng hay chọn thế".
- Chỉ số tính từ bản vẽ là dữ kiện. "Người dùng thích X" là suy luận; nói rõ khi nêu.
- Điều rút ra **dùng lại được cho dự án khác** và không dính số liệu hay tên dự án (ví dụ "hành lang hai bên bị loại khi hơn một phần ba số căn một mặt thoáng") thì ghi tri thức chung theo skill `knowledge-capture`. Người dùng chỉnh lại agent cũng là sự kiện cần cân nhắc ghi theo skill đó.
