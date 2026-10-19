---
name: construction-drawing-records
description: Quản lý bản vẽ trong giai đoạn thi công, gồm sử dụng hồ sơ được phát hành và cập nhật theo hiện trường; xác định bản vẽ nguồn, chứng cứ hiện trường hoặc phê duyệt thay đổi còn thiếu.
---

# Bản vẽ trong giai đoạn thi công

Nếu chưa rõ sản phẩm cần làm, dùng `construction-document-router` trước. Phân biệt bản vẽ thi công do đơn vị thiết kế lập, bản vẽ triển khai/gia công của nhà thầu và bản vẽ cập nhật khi có thay đổi. Tên gọi trong thực tế có thể giống nhau; xác định người lập, mục đích và trạng thái của từng tài liệu từ hồ sơ dự án.

## 1. Bản vẽ dùng để thi công

Xác định bản vẽ đã phát hành đang áp dụng, phiên bản, bộ môn và khu vực. So yêu cầu với hồ sơ thiết kế làm căn cứ và điều kiện thực tế ở công trường. Nếu lập chi tiết lắp đặt hoặc gia công cho nhà thầu, truy từng chi tiết về bản vẽ thiết kế chi phối và chỉ ra sai khác cần được xem xét. Không tự coi chi tiết do nhà thầu lập là thay đổi thiết kế đã được chấp thuận.

## 2. Cập nhật trong thi công

Với mỗi thay đổi được đề xuất hoặc ghi nhận, lưu: bản vẽ gốc và phiên bản; vị trí và các bộ môn bị ảnh hưởng; lý do và chứng cứ hiện trường; phương án mới; ảnh hưởng đến kích thước, giao diện, khối lượng và các bản vẽ liên quan; căn cứ quyết định/phê duyệt; bản vẽ sửa và phiên bản mới. Quan sát tại hiện trường chưa đủ để cho phép thay đổi thiết kế. Nếu thiếu phê duyệt, lập phương án đánh dấu “chờ xem xét” hoặc câu hỏi làm rõ.

## Sản phẩm và kiểm tra

Với cả hai loại việc, báo số hiệu/tên bản vẽ nếu có, phiên bản, trạng thái, tài liệu nguồn, nội dung đã sửa hoặc đề xuất, vấn đề còn mở và chứng cứ dùng để kiểm tra. Khi phù hợp, kiểm tra ảnh hưởng giữa các bộ môn và sự nhất quán giữa mặt bằng, mặt cắt, chi tiết, bảng biểu và khối lượng. Dùng `autocad-agent-coordinator` khi sửa bản vẽ qua AutoCAD MCP của dự án này.

Bản vẽ hoàn công thuộc giai đoạn 3. Nếu người dùng yêu cầu, chuyển sang giai đoạn đó và nói rõ bộ skill hiện chưa định nghĩa quy trình hoàn công.
