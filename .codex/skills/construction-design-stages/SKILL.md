---
name: construction-design-stages
description: Lập hoặc rà soát hồ sơ thiết kế xây dựng qua thiết kế cơ sở, thiết kế kỹ thuật và thiết kế bản vẽ thi công; xác định tài liệu làm căn cứ và đầu vào còn thiếu ở từng bước.
---

# Các bước thiết kế xây dựng

Nếu chưa rõ đang ở bước nào, dùng `construction-document-router` trước. Với mỗi bước, xác định sản phẩm cần bàn giao, tài liệu làm căn cứ, phiên bản, tình trạng rà soát/phê duyệt và phạm vi bộ môn. Số bước thiết kế và yêu cầu phê duyệt thực tế tuân theo hồ sơ của dự án.

## 1. Thiết kế cơ sở

**Mục đích:** xác lập giải pháp tổng thể và các thông số kỹ thuật chủ yếu.

**Đầu vào thường cần:** nhiệm vụ thiết kế; quy mô, công suất; khảo sát khu đất/hiện trạng; ràng buộc quy hoạch; tiêu chuẩn áp dụng; điểm đấu nối hạ tầng; giới hạn chi phí và tiến độ. Chỉ yêu cầu bổ sung mục còn thiếu nếu nó ảnh hưởng đến quyết định người dùng đang cần.

**Sản phẩm:** mặt bằng và giải pháp chính của các bộ môn liên quan, thông số chủ yếu, giả định, quyết định còn mở và những vấn đề phải xác minh trước thiết kế kỹ thuật. Ghi rõ đâu là phương án đang xem xét, đâu là phương án đã được chọn.

## 2. Thiết kế kỹ thuật

**Mục đích:** phát triển phương án đã chọn thành giải pháp kỹ thuật có tính toán và phối hợp giữa các bộ môn.

**Đầu vào thường cần:** phiên bản thiết kế cơ sở được phê duyệt hoặc chỉ định làm căn cứ; khảo sát và địa chất liên quan; tải trọng và tiêu chí thiết kế; yêu cầu thiết bị, hạ tầng; tiêu chuẩn kỹ thuật; quyết định của chủ đầu tư.

**Sản phẩm:** tính toán, chọn kích thước hệ thống, yêu cầu vật liệu/thiết bị, giao diện giữa các bộ môn, bản vẽ phối hợp và danh sách thay đổi so với hồ sơ làm căn cứ. Nêu rõ giao diện chưa giải quyết trước khi dùng hồ sơ để lập bản vẽ thi công.

## 3. Thiết kế bản vẽ thi công

**Mục đích:** thể hiện giải pháp của đơn vị thiết kế bằng kích thước, chi tiết, ghi chú, bảng biểu và tham chiếu đủ cho phạm vi xây lắp dự kiến.

**Đầu vào thường cần:** phiên bản thiết kế kỹ thuật được phê duyệt hoặc chỉ định làm căn cứ nếu dự án có bước này; bản vẽ/mô hình các bộ môn đã phối hợp; tính toán; thiết bị được chọn; điều kiện thi công và ý kiến rà soát.

**Sản phẩm:** danh mục bản vẽ có số hiệu/tên, tỷ lệ khi cần, kích thước, cao độ, cấu tạo, bảng vật liệu và ký hiệu, tham chiếu chéo, phiên bản và trạng thái phát hành. Xử lý xung đột hoặc thiếu sót ảnh hưởng đến khả năng thi công; ghi lại việc cần đơn vị thiết kế hoặc chủ đầu tư quyết định.

## Áp dụng ở mọi bước

- Trước khi sửa, xác định đúng dự án, bộ môn, khu vực, sản phẩm và phiên bản tài liệu nguồn.
- So yêu cầu với mục đích của bước hiện tại. Nếu cần mức chi tiết của bước sau, ghi rõ tình trạng phần bổ sung hoặc đề xuất đúng sản phẩm của bước kế tiếp.
- Tách biệt giả định thiết kế, số liệu khảo sát đã kiểm chứng, kết quả tính toán và nội dung phê duyệt. Ghi nguồn cho thông số ảnh hưởng lớn đến thiết kế.
- Rà soát sản phẩm với nhiệm vụ thiết kế, tính nhất quán nội bộ, giao diện giữa các bộ môn và tài liệu nguồn. Báo rõ nội dung đã kiểm tra và vấn đề còn mở.
- Mỗi lần lập mặt bằng tầng hoặc mặt bằng định vị tòa nhà, áp dụng [construction-boundaries-grids](../construction-boundaries-grids/SKILL.md) để kiểm tra chỉ giới, khoảng lùi của từng khối cao tầng/thấp tầng và hệ trục dùng chung. Khi thể hiện ký hiệu trục, đường nét, dùng thêm [construction-drawing-tcvn5570](../construction-drawing-tcvn5570/SKILL.md).
- Không tự ghi bản vẽ là “phát hành để thi công” chỉ vì bản vẽ đã đủ chi tiết; dùng trạng thái phát hành thực tế của dự án.

Với cập nhật hiện trường và bản vẽ triển khai/gia công của nhà thầu, dùng [construction-drawing-records](../construction-drawing-records/SKILL.md). Bản vẽ hoàn công thuộc giai đoạn 3 và chưa nằm trong bộ skill này.

Khi lập, sửa hoặc rà soát ký hiệu đường trục và đường nét trên bản vẽ thiết kế, dùng thêm [construction-drawing-tcvn5570](../construction-drawing-tcvn5570/SKILL.md).
