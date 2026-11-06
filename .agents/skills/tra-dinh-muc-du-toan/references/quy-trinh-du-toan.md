# Quy trình lập dự toán xây dựng

## Khung pháp lý (hiệu lực từ 01/07/2026)

| Văn bản | Nội dung chính |
|---|---|
| NĐ 206/2026/NĐ-CP | Nghị định khung quản lý chi phí đầu tư xây dựng (thay NĐ 10/2021) |
| TT 36/2026/TT-BXD | Tỷ lệ chi phí chung, TL, nhà tạm, mẫu bảng tổng hợp (Phụ lục III) |
| TT 37/2026/TT-BXD | Phương pháp xác định định mức, giá nhân công, giá ca máy, chỉ số giá (thay TT 13/2021, TT 01/2025) |
| TT 38/2026/TT-BXD | Ban hành định mức xây dựng (Phụ lục I-VIII) |
| CV 9947/BXD-VPB (29/6/2026) | Phụ lục thay thế cho TT 38 và Phụ lục V TT 36 (sửa sai sót) |

## Chuỗi tính dự toán

```
Chi phí trực tiếp  T = VL + NC + M
Chi phí chung      C = T × tỷ lệ C (Bảng 3.3 TT 36)
Chi phí không xác định KL  TT = T × tỷ lệ TT (Bảng 3.5 TT 36)
Chi phí gián tiếp  GT = C + TT
Thu nhập chịu thuế tính trước  TL = (T + GT) × tỷ lệ TL (Bảng 3.6 TT 36)
Giá trị dự toán XD trước thuế  GXDTT = T + GT + TL
Thuế GTGT          VAT = GXDTT × thuế suất (hiện 8% hoặc 10%)
Nhà tạm            LT = GXDTT × (1 + thuế suất) × tỷ lệ LT (Bảng 3.7 TT 36)
Dự phòng phát sinh GDP1 = (GXDTT + VAT + LT) × tỷ lệ %
Dự phòng trượt giá GDP2 = theo chỉ số giá XD
```

## Bảng tỷ lệ chi phí (TT 36/2026 Phụ lục III)

### Bảng 3.3 — Chi phí chung (dự toán), % trên T

| Loại công trình | ≤40 tỷ | ≤60 | ≤100 | ≤300 | ≤500 | ≤1000 | ≤2000 | >2000 |
|---|---|---|---|---|---|---|---|---|
| Dân dụng | 7,3 | 7,1 | 6,7 | 6,5 | 6,2 | 5,8 | 5,5 | 5,2 |
| Công nghiệp | 6,2 | 6,0 | 5,8 | 5,6 | 5,4 | 5,1 | 4,7 | 4,5 |
| Giao thông | 6,2 | 6,0 | 5,8 | 5,6 | 5,4 | 5,1 | 4,7 | 4,5 |
| Nông nghiệp & PTNT | 6,1 | 5,8 | 5,5 | 5,4 | 5,2 | 4,9 | 4,5 | 4,3 |
| Hạ tầng kỹ thuật | 5,5 | 5,3 | 5,1 | 5,0 | 4,8 | 4,5 | 4,2 | 4,0 |

Báo cáo KTKT (dự án chỉ lập BCKTKT): dùng cột riêng (cao hơn ~0,5-1%).
Vùng núi/biên giới/hải đảo: nhân hệ số 1,1.

### Bảng 3.2 — Chi phí chung (tổng mức đầu tư), % trên T

| Loại công trình | Tỷ lệ |
|---|---|
| Dân dụng | 7,3 |
| Công nghiệp | 6,2 |
| Giao thông | 6,2 |
| Nông nghiệp & PTNT | 6,1 |
| Hạ tầng kỹ thuật | 5,5 |

### Bảng 3.5 — Chi phí không xác định được khối lượng từ thiết kế (TT), % trên T

| Loại công trình | Tỷ lệ |
|---|---|
| Dân dụng | 2,5 |
| Công nghiệp, giao thông, nông nghiệp, hạ tầng | 2,0 |

### Bảng 3.6 — Thu nhập chịu thuế tính trước (TL), % trên (T + GT)

| Loại công trình | Tỷ lệ |
|---|---|
| Dân dụng | 5,5 |
| Công nghiệp | 6,0 |
| Giao thông | 6,0 |
| Nông nghiệp & PTNT | 5,5 |
| Hạ tầng kỹ thuật | 5,5 |

### Bảng 3.7 — Nhà tạm (LT), % trên GXDTT × (1 + thuế suất)

| Loại công trình | ≤100 tỷ | ≤500 | >500 |
|---|---|---|---|
| Công trình tuyến (giao thông, đường ống, đê điều...) | 2,2 | 2,0 | 1,7 |
| Công trình còn lại | 1,1 | 1,0 | 0,85 |

### Bảng 3.9 — Hạng mục khoán gọn (lump-sum)

Công tác không xác định được khối lượng chi tiết: dùng 50% tỷ lệ của các bảng trên.

### Lưu ý quan trọng

- Quy mô dự án tính bằng **chi phí xây dựng trước thuế** (không phải tổng mức đầu tư).
- Bảng 3.3 có **hai cột cho mỗi mức**: cột [2] cho dự toán thông thường, cột [3] cho BCKTKT.
- Vùng núi, biên giới, hải đảo, biển: nhân **hệ số 1,1** cho tất cả các bảng tỷ lệ.

## Công thức chi phí trực tiếp

Với một công tác có khối lượng Q và đơn vị tính của định mức:

- Vật liệu chính: Σ (hao phí vật liệu i × giá vật liệu i) × Q
- Vật liệu khác: (% vật liệu khác) × chi phí vật liệu chính
- Nhân công: hao phí công × đơn giá nhân công (đồng/công) × Q
- Máy: Σ (số ca máy j × giá ca máy j) × Q; máy phục vụ ghi theo % trên chi phí máy chính thì nhân %
- **Chi phí trực tiếp T = VL + NC + M**

## Hệ thống nhóm nhân công mới (TT 37/2026 Bảng 3.1)

Từ 01/07/2026, nhân công XD phân theo **nhóm**, không còn theo cấp bậc thợ (1/7→7/7):

| Phân loại | Nhóm | Công tác đại diện |
|---|---|---|
| **I. Nhân công XD** | Nhóm 1 | Chuẩn bị mặt bằng, phá dỡ, bốc xếp, đào đắp đất |
| | Nhóm 2 | Cọc, bê tông, cốt thép, ván khuôn, xây gạch, thảm BT nhựa |
| | Nhóm 3 | Lắp đặt HTKT, gia công kết cấu gỗ/thép, trát/ốp/lát/sơn, lắp điện |
| | Nhóm 4 | Đường dây tải điện, trạm biến áp, thiết bị CN, thông tin, thí nghiệm |
| **II. Vận hành máy** | Vận hành máy | Máy đào, cẩu, đóng cọc, trạm trộn, máy rải BT nhựa |
| | Lái xe | Cần trục ô tô, xe nâng, ô tô vận tải, xe bơm BT |
| | Thủy thủ/thợ máy | Tàu thuyền |
| | Máy trưởng | |
| | Thuyền trưởng | |
| **III. Đặc thù** | Kỹ sư KS/TN, thợ lặn, nghệ nhân, hầm lò | |

### Chuyển tiếp (Điều 2 TT 37)

- QĐ 1491/2024 (bậc thợ cũ) vẫn áp dụng đến khi Sở XD công bố giá nhóm mới (hạn chót 01/01/2027).
- Chuyển đổi: lấy bình quân giá các công tác đại diện trong nhóm. Ví dụ nhóm 1 ≈ 241.469 đ, nhóm vận hành ≈ 323.788 đ, nhóm lái xe ≈ 303.750 đ (số ví dụ trong TT 37, không phải số chính thức).
- Phần mềm dự toán (GXD 2026) có thể đã dùng giá chuyển đổi — giải thích vì sao giá trong file mẫu (228.618 đ) khác QĐ 1491 bậc 3.0/7 (265.915 đ).
- **Khi lập dự toán**: hỏi người dùng dùng giá nhóm chuyển đổi hay giá bậc thợ QĐ 1491; ghi rõ nguồn.

## Giá ca máy (TT 37/2026 Phụ lục IV)

```
CCM = CKH + CSC + CNL + CNC + CCPK
```

| Thành phần | Công thức | Giải thích |
|---|---|---|
| CKH (khấu hao) | Nguyên giá × %KH / Số ca năm | Khấu hao theo ca |
| CSC (sửa chữa) | Nguyên giá × %SC / Số ca năm | Bảo trì sửa chữa |
| CNL (nhiên liệu) | ĐM nhiên liệu × giá nhiên liệu | Diezel/xăng/điện |
| CNC (nhân công) | Giá NC vận hành × số người | Theo nhóm vận hành |
| CCPK (chi phí khác) | Nguyên giá × %CPK / Số ca năm | |

Bảng thông số 664+278 loại máy nằm trong TT 37 Phụ lục IV (nguyên giá, số ca năm, %KH, %SC, %CPK, ĐM nhiên liệu, nhân công vận hành).
QĐ 1491/2024 có **giá ca máy tính sẵn** cho Vùng I/II — dùng trực tiếp, không cần tính lại trừ khi cần cập nhật giá đầu vào.

## Cấp phối vữa bê tông và vữa xây

Có **hai bộ bảng cấp phối** trong CV 9947:

| Bộ | Vị trí trong PDF | Mã | Khi nào dùng |
|---|---|---|---|
| Phụ lục Chương VI (BT đổ tại chỗ) | Trang ~628-646 | C2xx, C3xx | **Lập dự toán** — phần mềm GXD dùng bộ này |
| Phụ lục VII (ĐMSD vật liệu) | Trang ~1666+ | 11.1xxxx | Quản lý sử dụng VL, không ghép trực tiếp vào đơn giá |

Khi tra cấp phối cho dự toán, dùng bộ **Phụ lục Chương VI** (mã C). Ví dụ C322 = BT M200 xi măng PCB40: xi măng 259 kg, cát 0,528 m³, đá 1×2 0,871 m³, nước 183 lít.

Hao hụt vật liệu thi công (5% = hệ số 1,05) lấy từ Phụ lục VII Phần 2.

## Ví dụ có kiểm: 1 m³ bê tông nền mác 200 (SB.41140, cấp phối C322)

Hao phí từ định mức: vữa BT 1,05 × 1 m³; VL khác 1%; nhân công nhóm 2: 1,54 công.

```
Xi măng PCB40:  259 × 1,05 × 1.250    = 339.938 đ
Cát vàng:       0,528 × 1,05 × 420.000 = 232.848 đ
Đá 1×2:         0,871 × 1,05 × 240.000 = 219.492 đ
Nước:           183 × 1,05 × 12        =   2.306 đ
VL khác 1%:                             =   7.946 đ
                              VL tổng   = 802.529 đ

NC nhóm 2:      1,54 × 228.618         = 352.072 đ
                              T (1 m³)  = 1.154.601 đ

Chi phí chung 6,2%:                       71.585 đ
TT 2%:                                    23.092 đ
TL 6%:                                    74.957 đ
                              GXDTT      = 1.324.235 đ
VAT 8%:                                  105.939 đ
Nhà tạm 1,1% × 1,08:                     15.744 đ
Dự phòng 6%:                              86.755 đ
                       Đơn giá dự thầu  = 1.531.595 đ  ✓
```

Ghi chú: file mẫu dùng tỷ lệ công nghiệp (6,2%/2%/6%) cho nhà dân dụng ≤40 tỷ — theo TT 36 đúng ra phải là 7,3%/2,5%/5,5%. Phần mềm GXD cho phép người dùng chọn.

## Danh sách kiểm trước khi trả kết quả

1. Mã hiệu và tên công tác khớp việc thực tế (loại vữa, mác, chiều rộng/cao, loại đất, biện pháp thủ công hay máy).
2. Đơn vị tính của định mức trùng đơn vị khối lượng bóc (1 m³, 100 m², 1 tấn...). Định mức nhiều bảng dùng "100 m²" hay "1 tấn", đừng nhân nhầm.
3. Chọn đúng cột điều kiện; đọc từ ảnh, không từ văn bản trích.
4. Đã đọc thuyết minh của chương: hệ số điều chỉnh (độ cao, mặt bằng chật hẹp, thi công trong nhà...).
5. Đơn giá đúng vùng, đúng năm, ghi nguồn; nói rõ nếu lệch năm so với định mức.
6. Tỷ lệ chi phí chung, TL, nhà tạm đúng **loại công trình** và **quy mô** (Bảng 3.3/3.5/3.6/3.7).
7. Khối lượng: từ bản vẽ nào, bóc theo quy tắc nào; trừ lỗ cửa, phần giao nhau. Khối lượng từ DWG đo bằng công cụ đo của MCP, không ước.
8. Mọi số trong bảng kết quả truy được về trang PDF hoặc bảng TT 36.

## Bóc khối lượng từ bản vẽ AutoCAD

Cần đo diện tích, chiều dài, đếm: nạp `autocad-agent-coordinator` rồi `autocad-identify-and-measure`; trích số có kèm layer và handle. Chỉ ra phần bản vẽ chưa đủ (không có mặt cắt thì không có chiều cao tường). Hỏi người dùng thay vì suy.

## Mẫu bảng báo cáo

| STT | Mã hiệu | Công tác | ĐVT | Khối lượng | Hao phí (VL / NC / máy) | Đơn giá dùng | Thành tiền | Trang nguồn |
|---|---|---|---|---|---|---|---|---|

Cuối báo cáo: giả định, nguồn giá (niêm yết/DMS/QĐ 1491), tỷ lệ áp dụng và căn cứ, mục chưa có căn cứ, tài liệu nên bổ sung.
