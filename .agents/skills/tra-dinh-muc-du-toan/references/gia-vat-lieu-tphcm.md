# Giá vật liệu xây dựng TP.HCM (thư mục "CONG BO GIA VLXD THANG 6-2026")

Thư mục có 166 file (213 MB): 1 thông báo chính, 2 phụ lục giá đá/cát (mỗi phụ lục một bản PDF ký số và một bản `.txt`; trích ra khớp nhau), và 161 file trong thư mục `BẢNG GIÁ` của doanh nghiệp, chia theo 25 nhóm. Tìm giá bằng `scripts/tra_gia_vlxd.py`; file này nói thư mục chứa gì và dùng thế nào cho đúng.

## Thông báo chính

Thông báo số 24594/TB-SXD-KTVLXD của Sở Xây dựng TP.HCM, công bố giá vật liệu xây dựng tháng 6/2026 (phụ lục ghi ngày 08/7/2026; bản PDF chưa điền ngày ở đầu). Căn cứ: Luật Giá 16/2023, Luật Xây dựng, NĐ 10/2021, TT 11/2021 (sửa đổi bởi TT 14/2023, 01/2025, 60/2025). Điểm phải nhớ (mục II):

1. Giá theo **niêm yết của doanh nghiệp** có tham khảo thị trường; **chưa loại trừ chiết khấu, hoa hồng, ưu đãi**.
2. **Không dùng để thanh quyết toán.**
3. Vật liệu chưa có trong công bố, hoặc không phù hợp công trình: chủ đầu tư/tư vấn xác định giá theo TT 36/2026/TT-BXD và TT 37/2026/TT-BXD (cùng ngày 26/6/2026), tự chịu trách nhiệm.
4. Nhiều doanh nghiệp vẫn nêu QCVN 16:2019/BXD vì giấy chứng nhận hợp quy còn hiệu lực.
5. Có mục riêng về vật liệu chống cháy (đọc nguyên văn mục II.6 khi liên quan).

Phụ lục 1: giá đá, cát của doanh nghiệp khai thác khoáng sản trên địa bàn TP.HCM (kèm điều kiện thương mại, trữ lượng). Phụ lục 2: giá tham khảo thị trường từ báo cáo của UBND 8 phường, xã (Bình Tân, Chánh Hưng, Gia Định, Hòa Lợi, Phú Thọ, Tân Sơn Nhì, Thạnh Mỹ Tây, Thái Mỹ); chỉ 1 đơn vị báo cáo cơ bản đúng quy định. Hai phụ lục có bản `.txt` đã trích (`pl1.txt`, `pl2.txt`) và bản PDF ký số; bản PDF ký số có chữ.

## 25 nhóm, nhóm nào có dữ liệu

| Nhóm | Vật liệu | Có số liệu trong thư mục |
|---|---|---|
| 1 | Thép xây dựng | Thép Miền Nam (VNSTEEL), Vina Kyoei: **chỉ PDF quét** |
| 2 | Xi măng | Thăng Long, Vicem Hà Tiên, Cẩm Phả, Fico-YTL, Hạ Long, Phát triển Sài Gòn (Excel) |
| 3 | Vữa | Không có |
| 4 | Dây, cáp điện | CADIVI (Excel, công bố từ 8/2025 đến hết 7/2026) |
| 5 | Ống cống, cọc bê tông | Hùng Vương |
| 6 | Vật liệu lợp | Tôn Pomina (CV 17/12/2025) |
| 7 | Gạch không nung | Đại Dũng, Lê Hùng, Bình Dương |
| 8 | Ốp lát | Thạch Bàn Sài Gòn, Sơn Thạch, Đồng Tâm |
| 9 | Đá | Tân Cang (**tháng 8-9/2024**), Phụ lục 1 và 2 |
| 10 | Cát | Tân Cang (2024), Phụ lục 1 và 2 |
| 11 | Coffa | Không có |
| 12 | Bê tông nhựa nóng | Anco, Giao thông Sài Gòn |
| 13 | Nhựa đường nhũ tương | Giao thông Sài Gòn, ADCo |
| 14 | Bê tông thương phẩm | Hodeco, Việt Hàn |
| 15 | Trụ đèn | Không có |
| 16, 17 | Vải địa kỹ thuật, rọ đá | Liên Phát |
| 18 | Sơn, bột bả | 10 hãng: Hoàng Gia, Sơn Hà Nội, Nippon, Kova, Hòa Bình, Sivico, TOA, Akzo Nobel, Revolution, Jotun |
| 19 | Tấm thạch cao | Không có |
| 20 | Ống nhựa | Châu Âu Xanh, Đạt Hòa, Tiền Phong (**chỉ PDF quét**) |
| 21 | Bóng đèn, phụ kiện điện | Tín Lợi, Hưng Phú Hải, Thiên Minh, Mạnh Phương |
| 22 | Cửa | Alumin Japan, Đại Tân Thành, Cty 125, Nam Sung |
| 23 | Kính xây dựng | Không có |
| 24 | Màng phản quang | Đỉnh Phương Nam |
| 25 | Khác | Sigen, GPS, Busadco, Bestmix, Indecons |

Nhóm không có đơn vị công bố (vữa, coffa, trụ đèn, thạch cao, kính): không có giá trong thư mục này, hỏi người dùng hoặc báo giá riêng, không lấy từ nhóm khác.

## Dạng file và cách đọc

- **Excel** (85 xlsx, 5 xls): bảng niêm yết theo mẫu của TT 14/2023 (Mẫu 01 Phụ lục VIII) hoặc mẫu VII.2. Cột chính: Nhóm vật liệu, Tên vật liệu, Đơn vị, tiêu chuẩn, quy cách, nhà sản xuất, xuất xứ, điều kiện thương mại, vận chuyển, ghi chú, **giá bán chưa gồm VAT**, rồi cột "chênh lệch so với kỳ trước" (% tăng giảm). Một doanh nghiệp thường nộp 2-3 file giống nhau (mẫu VII.2, mẫu VIII, "file 737"); script bỏ dòng trùng.
- **PDF** (69 file): phần lớn là bản **quét không có chữ** (công văn và bảng giá ký đóng dấu); xem ảnh. Trang bảng giá hay xoay ngang: xoay 90° khi dựng ảnh, DPI 150-170 mới đọc được số.
- **.doc** (3 file: Bestmix, GPS, Đỉnh Phương Nam): chưa đọc được (công cụ trích chữ trả về rỗng); tên file là công văn đề nghị công bố giá. Mở bằng Word khi cần. `.txt` ngắn (như `ton.txt`) gần như không có nội dung.

## Số đọc được từ ảnh, giá thép (chưa VAT, đ/tấn, khu vực TP.HCM)

**VNSTEEL / Thép Miền Nam** (CV 362/TMN-KD ngày 29/4/2026; bảng ghi áp dụng từ 08/4/2026 đến khi có thông báo mới, còn công văn ghi 06/5/2026: hai ngày lệch nhau, hỏi hoặc ghi cả hai):

| Loại | Giá |
|---|---|
| Thép cuộn Φ6 (cán kéo, không logo) | 14.100.000 |
| Thép cuộn Φ6, Φ8 (CB240-T) | 15.660.000; 15.610.000 |
| Thanh vằn D10 CB300-V | 15.760.000 |
| Thanh vằn D12-25 CB300-V | 15.660.000 |
| Thanh vằn D10 CB400-V | 15.800.000 |
| Thanh vằn D12-D32 CB400-V | 15.700.000 |
| Thanh vằn D36-D43 CB400-V | 16.100.000 |
| Thanh vằn D10 CB500-V | 15.800.000 |
| Thanh vằn D12-D32 CB500-V | 15.700.000 |
| Thanh vằn D36-D43 CB500-V | 16.100.000 |

Ghi chú của bảng: giá chưa trừ chiết khấu sản lượng; CB400-V/CB500-V là giá đã trừ hết chiết khấu sản lượng tháng; giao tại kho công ty ở Phú Mỹ, Thủ Đức; có điều chỉnh khi giao tại Nhà Bè (Đồng Nai); kỳ trước đến nay giảm khoảng 2,5 %.

**Thép Vina Kyoei** (CV 04.26/VKS-KKG ngày 03/4/2026), giao trên phương tiện bên mua tại KCN Phú Mỹ I: thép cuộn Φ6-Φ8 CB240-T/CB300-T 16.800.000; thanh vằn CB300-V D10 17.000.000, D12-25 16.800.000; SD295 D10 17.000.000, D16 16.800.000; CB400-V D10 17.000.000; kỳ trước đến nay tăng khoảng 4,3 %. Bảng còn các trang sau (6 trang), chưa đọc hết hàng CB400-V, CB500-V các cỡ lớn.

**Cảnh báo:** hai hãng lệch nhau khoảng 1,1-1,3 triệu đ/tấn do điều kiện giao hàng và chiết khấu khác nhau; không trộn hai nguồn trong cùng một dự toán mà không nói.

## Quy ước chọn giá: lấy giá niêm yết

Đơn giá lấy từ **Bảng niêm yết giá** (Mẫu 01 Phụ lục VIII TT 14/2023): cột "Giá bán (chưa bao gồm thuế GTGT)". Dùng `search --niem-yet` để chỉ lọc sheet loại này; file mẫu VII.2, "file 737", sheet `Sheet1`, báo giá không dùng cho đơn giá. Bảng niêm yết nhiều khi in thêm ở dòng ghi chú ngày hiệu lực; ghi ngày đó vào báo cáo.

## Cạm bẫy đã gặp khi tra

- **Cùng một file, hai sheet, hai giá.** Hodeco: bê tông M300 là **1.572.000** ở sheet `Sheet1` (còn cột 1.422.000 và 150.000 chưa rõ nghĩa) nhưng **1.564.074** ở sheet `NY` (bảng niêm yết theo Mẫu 01, ghi chênh lệch +0,11 %). Người dùng đã chốt **lấy giá niêm yết**, nên Hodeco M300 dùng **1.564.074** (sheet `NY`).
- **Cột chưa VAT và có VAT** nằm cạnh nhau. Xi măng Vicem Hạ Long PCB40 bao: 1.259.259 (TP.HCM, chưa VAT) và 1.360.000 (đúng 1.259.259 × 1,08, nên là giá có thuế); khu vực Cần Giờ, Củ Chi có cột riêng. Luôn mở `rows` đọc dòng tiêu đề để biết cột nào là gì.
- **Nhiều khu vực** (TP.HCM, Cần Giờ, Củ Chi; có hãng thêm Nha Trang, Phú Quốc, Cần Thơ, Đà Nẵng) trong cùng dòng: chọn đúng khu vực của công trình.
- **Điều kiện thương mại**: giao tại nhà máy hay tại công trình, có gồm vận chuyển không, bao 50 kg hay xá, có bơm không (bê tông). Hai giá chỉ so được khi cùng điều kiện.
- **Đơn vị**: xi măng tính tấn (đồng/tấn) dù bán theo bao 50 kg; sơn theo lon hay thùng; bê tông theo m3. Đổi sang đơn vị của định mức (kg xi măng, lít sơn) trước khi nhân.
- **Giá cũ**: đá, cát Tân Cang là tháng 8-9/2024; CADIVI công bố từ 8/2025; Thăng Long giữ giá 2025. Báo tuổi của nguồn khi dùng.
- Giá công bố tháng 6/2026 nhưng nhiều file ghi "đến khi có thông báo mới" hay hiệu lực đến cuối 2026; kiểm ngày hiệu lực trong ghi chú.

## Ghép với định mức

Định mức (xem `cau-truc-tai-lieu.md`) cho hao phí theo vật liệu; vật liệu hay là "vữa bê tông" hay "vữa xây" nên cần cấp phối ra xi măng, cát, đá, hoặc dùng **bê tông thương phẩm** (nhóm 14, giá m3 tại công trình) thay cho vữa trộn tại chỗ, và **nói rõ lựa chọn đó**. Giá nhân công, ca máy lấy ở QĐ 1491/2024 (lệch năm so với giá vật liệu 2026).
