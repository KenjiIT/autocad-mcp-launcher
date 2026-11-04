# Cấu trúc hai tài liệu đã nạp

Mọi số ở đây tôi đã thấy trực tiếp trong file; chỗ suy ra thì ghi "suy ra".

## 1. CV 9947/BXD-VPB, phụ lục thay thế (PDF 1.895 trang, có chữ)

Công văn ngày 29/6/2026 gửi phụ lục thay thế cho TT 38/2026/TT-BXD (ban hành định mức xây dựng, Phụ lục I-VIII) và Phụ lục V của TT 36/2026/TT-BXD (chi phí đầu tư xây dựng), vì phát hành sai sót. Ngày ban hành hai thông tư: 26/6/2026.

| Phụ lục TT 38/2026 | Nội dung | Trang PDF (khoảng) |
|---|---|---|
| I | Định mức dự toán khảo sát xây dựng | 2-143 |
| II | Định mức dự toán xây dựng công trình | 144-... (phần lớn tệp) |
| III | Lắp đặt hệ thống kỹ thuật của công trình | sau II |
| IV | Lắp đặt máy và thiết bị công nghệ | |
| V | Thí nghiệm chuyên ngành | |
| VI | Sửa chữa và bảo dưỡng công trình | |
| VII | Định mức sử dụng vật liệu | |
| VIII | Định mức chi phí quản lý dự án và tư vấn | |
| (TT 36) V | Biểu mẫu dự toán chi phí khảo sát; cuối tệp (trang 1895) | |

Trang chính xác của từng phụ lục: `search <pdf> "Phụ lục V kèm theo"` rồi đọc trang tiêu đề.

### Phụ lục II: 13 chương và tiền tố mã (suy ra từ thứ tự chương và tên nhóm đầu)

| Chương | Công tác | Tiền tố |
|---|---|---|
| I | Chuẩn bị mặt bằng xây dựng (gồm tháo dỡ) | AA |
| II | Thi công đất, đá, cát | AB |
| III | Thi công cọc | AC |
| IV | Thi công đường | AD |
| V | Xây gạch, đá | AE |
| VI | Kết cấu bê tông (đổ, cốp pha, cốt thép) | AF |
| VII | Bê tông đúc sẵn | AG |
| VIII | Gia công, lắp dựng cấu kiện gỗ | AH |
| IX | Gia công, lắp dựng cấu kiện sắt thép | AI |
| X | Hoàn thiện (mái, trát, láng, ốp, lát, sơn...) | AK |
| XI | Các công tác khác | AL |
| XII | Bốc xếp, vận chuyển vật liệu và cấu kiện | AM |
| XIII | Sử dụng tro xỉ nhiệt điện | AN |

Đã kiểm: AF.10000 là đổ bê tông thủ công, AE.20000 xây gạch đất sét nung, AK.21000 trát tường, AM.10000 bốc xếp thủ công, AH.10000 gia công vì kèo, AI.10000 gia công cấu kiện sắt thép. Với các tiền tố còn lại, mở trang kiểm lại trước khi tin.

### Cách đọc một bảng định mức

Ví dụ thật, trang PDF 477 (in số 333):

```
AF.11200 BÊ TÔNG MÓNG                   Đơn vị tính: 1 m3
Mã hiệu AF.112  Bê tông móng             cột: Chiều rộng ≤250 cm | >250 cm
  Vật liệu       Vữa bê tông   m3        1,025 | 1,025
                 Vật liệu khác %         1     | 5
  Nhân công nhóm 2          công         1,23  | 1,48
  Máy thi công   Máy trộn 250 l  ca      0,095 | 0,095
                 Máy đầm dùi 1,5 kW ca   0,089 | 0,089
  Mã cột                                 10    | 20
```

- Hao phí tính cho **một đơn vị tính** của công tác (ở đây 1 m3).
- "Vật liệu khác" là **% trên chi phí vật liệu chính**, không phải khối lượng.
- Hàng cuối "10 | 20" là mã cột; mã đầy đủ thường là mã dòng ghép mã cột (ở đây AF.112 với 10 thành AF.11210; mã này tôi chưa thấy in nguyên chữ, kiểm trong mục lục trước khi ghi ra hồ sơ).
- "Vữa bê tông" là vật liệu bán thành phẩm; muốn ra xi măng, cát, đá phải tra định mức cấp phối vữa bê tông (cùng tập, hoặc Phụ lục VII, định mức sử dụng vật liệu).
- Điều kiện cột (chiều rộng, chiều cao ≤6 m, ≤28 m, ≤100 m, ≤200 m...) quyết định chọn cột nào. Độ cao tính từ cốt ±0.00.
- Thi công ở độ cao lớn: công tác trát, láng, ốp không ghi độ cao, trên 6 m cộng thêm định mức bốc xếp vật liệu lên cao.
- Định mức thủ công chỉ dùng khi điều kiện thi công không làm được bằng máy.
- Mỗi chương có thuyết minh và hướng dẫn áp dụng riêng; **đọc phần đó trước bảng**, vì có hệ số điều chỉnh theo điều kiện.

## 2. QĐ 1491/QĐ-SXD-KT&VLXD (PDF quét, 46 trang)

Sở Xây dựng TP.HCM ký ngày 31/12/2024: công bố đơn giá nhân công, giá ca máy và thiết bị thi công năm 2024 trên địa bàn TP.HCM (Phụ lục I, II). Dùng làm cơ sở cho dự án vốn đầu tư công; dự án ngoài vốn đầu tư công chỉ khuyến khích tham khảo (Điều 1). Căn cứ pháp lý là Nghị định 10/2021, Thông tư 11/2021, 13/2021, 14/2023 (khung cũ).

- **Vùng I** (Thủ Đức, Quận 1, 3, 4, 5, 6, 7, 8, 10, 11, 12, Phú Nhuận, Bình Thạnh, Tân Phú, Gò Vấp, Tân Bình, Bình Tân, Bình Chánh, Nhà Bè, Hóc Môn, Củ Chi); **Vùng II** (Cần Giờ).
- Phụ lục I, nhân công (đồng/công), đọc được từ ảnh trang 3:

| Cấp bậc | Hệ số | Vùng I | Vùng II |
|---|---|---|---|
| 1,0/7 | 1 | 191.306 | 176.882 |
| 2,0/7 | 1,18 | 225.741 | 208.721 |
| 3,0/7 | 1,39 | 265.915 | 245.866 |
| 3,5/7 | 1,52 | 290.785 | 268.861 |
| 4,0/7 | 1,65 | 315.655 | 291.856 |
| 5,0/7 | 1,94 | 371.133 | 343.152 |
| 6,0/7 | 2,30 | 440.004 | 406.829 |
| 7,0/7 | 2,71 | 518.439 | 479.351 |

  Các hàng này lặp giống nhau cho nhóm I và II trong trang đã xem; chưa xem nhóm III trở đi, nên không suy ra bảng đầy đủ.
- Phụ lục II, giá ca máy: mỗi máy một dòng, có số ca năm, % khấu hao, % sửa chữa, % chi phí khác, định mức nhiên liệu, thành phần thợ điều khiển, nguyên giá tham khảo, chi phí nhiên liệu, nhân công điều khiển và giá ca máy cho Vùng I và Vùng II. Ví dụ trang 5: M102.0502 cẩu tự hành 100 t, giá ca máy Vùng I 10.430.299 đ. **Máy cụ thể (máy trộn 250 l, máy đầm dùi 1,5 kW...) phải đọc từ ảnh trang tương ứng**; chưa tra.

Chưa làm: ghép tên nhóm nhân công trong định mức 2026 ("nhóm 2") với "nhóm II" và bậc thợ của bảng 2024.
