# Quy trình lập dự toán chi phí trực tiếp

## Công thức

Với một công tác có khối lượng Q và đơn vị tính của định mức:

- Vật liệu chính: Σ (hao phí vật liệu i × giá vật liệu i) × Q
- Vật liệu khác: (% vật liệu khác) × chi phí vật liệu chính
- Nhân công: hao phí công × đơn giá nhân công (đồng/công) × Q
- Máy: Σ (số ca máy j × giá ca máy j) × Q; máy phục vụ ghi theo % trên chi phí máy chính thì nhân %
- **Chi phí trực tiếp = vật liệu + nhân công + máy**

Đơn giá vật liệu không có trong hai tài liệu đã nạp; lấy từ công bố giá vật liệu địa phương hoặc báo giá, nói rõ nguồn và thời điểm. Chi phí chung, thu nhập chịu thuế tính trước, thuế GTGT, nhà tạm, dự phòng: tỷ lệ ở TT 36/2026 (chưa nạp), hỏi người dùng hoặc nạp thêm; không đoán.

## Ví dụ có kiểm: 1 m3 bê tông móng, chiều rộng ≤250 cm (AF.112, cột đầu)

Hao phí từ trang PDF 477: vữa bê tông 1,025 m3; vật liệu khác 1 %; nhân công nhóm 2: 1,23 công; máy trộn 250 l: 0,095 ca; máy đầm dùi 1,5 kW: 0,089 ca.

Phần nhân công dạng công thức (đơn giá điền sau):
nhân công = 1,23 × đơn giá công (nhóm 2, bậc theo hướng dẫn) ; ví dụ nếu bậc 3,5/7 Vùng I là 290.785 đ thì 1,23 × 290.785 = 357.666 đ/m3. Đây chỉ minh họa phép tính; bậc thợ thật phải xác định theo thông tư.

Giá vữa bê tông, giá ca máy trộn và máy đầm dùi: chưa có số trong ví dụ, không điền.

## Danh sách kiểm trước khi trả kết quả

1. Mã hiệu và tên công tác khớp việc thực tế (loại vữa, mác, chiều rộng/cao, loại đất, biện pháp thủ công hay máy).
2. Đơn vị tính của định mức trùng đơn vị khối lượng bóc (1 m3, 100 m2, 1 tấn... ). Định mức nhiều bảng dùng "100 m2" hay "1 tấn", đừng nhân nhầm.
3. Chọn đúng cột điều kiện; đọc từ ảnh, không từ văn bản trích.
4. Đã đọc thuyết minh của chương: hệ số điều chỉnh (độ cao, mặt bằng chật hẹp, thi công trong nhà...).
5. Đơn giá đúng vùng, đúng năm, ghi nguồn; nói rõ nếu lệch năm so với định mức.
6. Khối lượng: từ bản vẽ nào, bóc theo quy tắc nào; trừ lỗ cửa, phần giao nhau. Khối lượng từ DWG đo bằng công cụ đo của MCP, không ước.
7. Mọi số trong bảng kết quả truy được về trang PDF.

## Bóc khối lượng từ bản vẽ AutoCAD

Cần đo diện tích, chiều dài, đếm: nạp `autocad-agent-coordinator` rồi `autocad-identify-and-measure`; trích số có kèm layer và handle. Chỉ ra phần bản vẽ chưa đủ (không có mặt cắt thì không có chiều cao tường). Hỏi người dùng thay vì suy.

## Mẫu bảng báo cáo

| STT | Mã hiệu | Công tác | ĐVT | Khối lượng | Hao phí (VL / NC / máy) | Đơn giá dùng | Thành tiền | Trang nguồn |
|---|---|---|---|---|---|---|---|---|

Cuối báo cáo: giả định, mục chưa có căn cứ (đơn giá vật liệu, tỷ lệ chi phí chung, thuế), tài liệu nên bổ sung.
