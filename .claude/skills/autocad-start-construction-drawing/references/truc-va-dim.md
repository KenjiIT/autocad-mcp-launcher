# Dựng trục và kích thước (dim) trong AutoCAD qua MCP

Học từ bản `CR8-2B --Sheet - A-202 - MẶT BẰNG TẦNG 1.dwg` (kiến trúc, mặt bằng tầng 1) và thử vẽ lại trên một nhà nhỏ 8 × 10 m ở tỉ lệ 1:100 (AutoCAD đầy đủ). Số liệu ở đây là **ví dụ đã đo**, không phải chuẩn bắt buộc; kích thước, tên layer và vị trí lấy theo bản vẽ đang làm.

**Căn cứ trước khi vẽ:** vị trí trục phải do người dùng cung cấp, xác nhận, hoặc lấy từ một bản vẽ đã chọn làm căn cứ (xem mục "Chặn vẽ trục" của `SKILL.md`). Chỉ dựng trục theo vị trí đó, không tự chia nhịp. Ký hiệu trục theo `construction-drawing-tcvn5570`.

## 1. Bản CR8-2B dựng trục và dim như thế nào (đã đọc bằng COM, chỉ đọc)

- Đơn vị mm (`INSUNITS` 4). Bản vẽ lớn (3.954 đối tượng): đọc trực tiếp qua COM bằng script chỉ đọc, không đọc qua MCP (xem "Bản vẽ lớn" của `autocad-agent-coordinator`).
- **Trục** là các `LINE` chạy suốt công trình, trên layer riêng (`A-COLS-GRID-1`): màu ACI 8, nét `Grid Line` (trông gần như liền), lineweight mảnh. Đối tượng để `ByLayer`.
- **Đánh số:** trục đứng 1, 1A, 1B... từ trái sang phải; trục ngang A, A1, A2, B, C, C1, E, F, G, H từ dưới lên (bỏ chữ D). Trục xiên ngắn đặt thêm một đoạn.
- **Nhãn trục:** vòng tròn đặt ngoài đầu trục (trục đứng ở đáy, trục ngang ở bên trái), kèm chữ MTEXT cao 600 mm, font Arial, layer riêng (`A-COLS-BUBL`). Vòng là khối `Grid - 10 mm...` chèn tỉ lệ 150; tỉ lệ in suy ra khoảng 1:150 (chưa xác nhận).
- **Dim giữa các trục** (layer `G-DIMS`, màu 1 đỏ, kiểu `0_MP500_NOLINE`): chuỗi dim giữa các trục liền kề cộng một dim tổng đặt xa công trình hơn. Chữ không ghi đè (`TextOverride` rỗng), lấy số đo thật, làm tròn mm. Chữ cao khoảng 2,5 mm trên giấy.
- **Kiểu dim `NOLINE`:** **không có mũi tên**. Đầu dim là vạch xiên nhỏ (`Arrowhead1Type = 5`, khối `Oblique`) và **không có đường gióng** (đường trục đã đóng vai trò gióng). Dim nằm trong vùng đường trục kéo dài, giữa công trình và vòng nhãn.

## 2. Thứ tự dựng bằng MCP

1. **Căn cứ và dọn cũ.** Có trục hoặc dim cũ cần thay thì xóa bằng `delete_batching` (không hoàn tác được; hỏi người dùng nếu chưa được dặn).
2. **Đặt biến theo tỉ lệ in** bằng `drawing set_variables` (kèm `doc_id`, `expected_revision`, `lease_token`, `worker_generation`): `DIMSCALE` = mẫu số tỉ lệ (1:100 thì 100), `DIMTXT` 2,5, `DIMASZ` 2, `LTSCALE` (xem mục 3). Biến này **không** tự áp cho dim tạo qua công cụ trên AutoCAD đầy đủ (xem mục 4).
3. **Tạo trục** bằng `cad_batch`: mỗi trục một `create_line` trên layer trục; kéo ra ngoài tường một đoạn đủ chứa vòng nhãn. Tham số đặt trong `params`: `{"op": "create_line", "params": {"x1":..., "y1":..., "x2":..., "y2":..., "layer": "A-GRID"}}`.
4. **Tạo vòng nhãn và chữ** cùng lô: `create_circle` (tâm = đầu trục lùi ra một bán kính, để đầu trục tiếp xúc vòng) và `create_text` trên layer nhãn.
5. **Tạo dim:** đặt layer hiện hành là layer dim (`layer set_current`), rồi `annotation create_dimension_linear` với hai điểm trên hai trục và điểm đặt đường dim. Đặt hai điểm đo nằm **ngay trên đường dim** (cùng `y` cho dim ngang, cùng `x` cho dim đứng) để khỏi sinh đường gióng dài đè lên trục.
6. **Đổi đầu dim thành vạch xiên và bỏ đường gióng** (mục 4, công cụ chưa làm được).
7. **Kiểm tra** (mục 5).

## 3. Con số đã thử ở tỉ lệ 1:100 (nhà 8 × 10 m, trục 1–2 và A–B–C)

| Thành phần | Giá trị (mm) | Ghi chú |
|---|---:|---|
| Trục kéo ra ngoài | 2.200 so với đầu trục tới tâm vòng 400 | Đầu trục tiếp xúc vòng |
| Vòng nhãn | Ø 800 (bán kính 400) | TCVN 5570: 8 mm giấy khi tỉ lệ từ 1:200 tới 1:100 |
| Chữ nhãn | cao 400 | Căn giữa vòng (xem dưới) |
| Chuỗi dim | cách tường 1.000 | |
| Dim tổng | cách tường 1.700 | Xa hơn chuỗi dim |
| Chữ dim | 2,5 mm giấy = 250 | `DIMTXT` × `DIMSCALE` |
| Vạch xiên | 1,5 mm giấy = 150 | `ArrowheadSize` 1,5 với `ScaleFactor` 100 |

- **Căn giữa chữ trong vòng:** `create_text` chèn theo góc trái dưới, nên với chữ cao 400: số `1`, `2` đặt `x = cx − 120`; chữ `A`, `B` đặt `x = cx − 135`; chữ `C` đặt `x = cx − 145`; mọi chữ đặt `y = cy − 145`. Kiểm tra lại bằng ảnh.
- **`LTSCALE`:** mẫu `CENTER` trong bản vẽ này theo đơn vị inch (gạch dài 1,25 đơn vị). `LTSCALE` = mẫu số × 25,4 (1:100 thì 1270) cho gạch dài khoảng 16 mm giấy. Đặt bằng mẫu số (50) thì gạch dài chỉ khoảng 62 mm model, trông như nét liền. Bản vẽ có kiểu nét mét (`acadiso`) thì dùng thẳng mẫu số.

## 4. Bẫy đã gặp (AutoCAD đầy đủ)

- **Dim tạo qua công cụ không lấy `DIMSCALE`:** dim ra với `ScaleFactor = 1`, chữ cao 2,5 mm trong mô hình mét, nhỏ gấp 100 lần so với bản in. Cách làm tạm: đặt `ScaleFactor` của dim bằng mẫu số. Bản mã đã sửa (`_finish_dimension` trong `file_ipc.py`) tự áp `DIMSCALE`, nhưng chỉ có hiệu lực sau khi khởi động lại launcher; kiểm `entity get` sau khi tạo.
- **`create_dimension_*` với `layer` có thể báo `TypeError`** trên bản mã cũ (tham số `layer` và `text` chỉ có ở bản LT). Bản mã đã sửa nhận cả hai. Chưa chắc launcher đang chạy là bản mới thì đặt layer hiện hành rồi không truyền `layer`.
- **Công cụ không chọn được kiểu đầu dim, không bỏ được đường gióng, chỉ đặt được `DIMSCALE`, `DIMTXT`, `DIMASZ`.** Đổi đầu dim thành vạch xiên và bỏ đường gióng phải đặt trực tiếp trên từng dim bằng COM (ngoài MCP; nói rõ với người dùng): `Arrowhead1Type = 5`, `Arrowhead2Type = 5`, `ArrowheadSize = 1.5`, `ExtLine1Suppress = True`, `ExtLine2Suppress = True`, `DimensionLineExtend = 1.0`. Tên thuộc tính đúng là `ExtLine1Suppress` (không phải `ExtensionLine1Suppress`).
- **Không tin bảng mã loại mũi tên theo trí nhớ:** mã `12` ra vòng tròn nhỏ ở bản AutoCAD này, còn mã `5` ra vạch xiên (đúng giá trị dim CR8-2B đang dùng). Luôn đọc `Arrowhead1Type` từ một dim nguồn rồi chụp ảnh phóng gần để xác nhận.
- **Chuyển tab bằng COM (`Activate`) làm AutoCAD từ chối lệnh kế tiếp** (`Call was rejected by callee`): thử lại sau nửa giây. Lệnh `view zoom_window` áp cho tab đang hoạt động; kiểm tab trước khi phóng, kẻo đổi khung nhìn của bản nguồn.
- **COM không đọc được điểm định nghĩa của dim cũ** (`XLine1Point` và các tên tương tự đều lỗi qua gọi muộn), nên không tái dựng được dim cũ từ điểm cũ; dựng lại theo trục.
- **Dim tổng và chữ dim đứng có thể chen với đường trục và vòng nhãn:** CR8-2B cũng bố trí tương tự; chấp nhận hoặc đẩy dim tổng xa hơn.

## 5. Kiểm tra sau khi vẽ

- `entity get` từng dim: `measurement` bằng khoảng cách trục (ví dụ 7780, 4890, 9780); `text` rỗng.
- `entity count` theo layer trục, nhãn, dim khớp số đã tạo.
- Ảnh `view get_screenshot` toàn bản và phóng gần một đầu dim: không có mũi tên, vạch xiên đúng, nét trục có gạch dài nhìn thấy, chữ nhãn nằm giữa vòng, chữ dim đọc được ở tỉ lệ in.
- Báo rõ phần chưa làm được qua MCP (kiểu đầu dim, đường gióng) và việc bản vẽ chưa lưu.
