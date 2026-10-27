---
name: construction-document-router
description: Xác định yêu cầu hồ sơ xây dựng thuộc giai đoạn và bước nào (thiết kế, thi công, hoàn công), kiểm tra đầu vào còn thiếu, rồi chuyển sang skill thiết kế hoặc thi công. Dùng khi người dùng đưa nhiệm vụ, bản vẽ, mô hình hoặc thay đổi hiện trường mà chưa nói rõ đang ở bước nào.
---

# Xác định giai đoạn hồ sơ xây dựng

Phân loại theo **sản phẩm người dùng muốn có**, không chỉ theo tên hoặc ngày của tài liệu đính kèm. Một dự án có thể đồng thời có việc thiết kế và thi công.

## Tiếp nhận và phân luồng

1. Đọc yêu cầu và tài liệu sẵn có. Xác định sản phẩm cần bàn giao, bộ môn, dự án/khu vực, phiên bản hồ sơ, tình trạng phê duyệt và nguồn chứng cứ. Phân biệt thông tin do người dùng cung cấp, quan sát được, suy luận hoặc chưa biết. Không coi suy luận là phê duyệt hay sự thật hiện trường.
2. Chọn luồng:
   - **Giai đoạn 1 — thiết kế:** thiết kế cơ sở, thiết kế kỹ thuật hoặc thiết kế bản vẽ thi công. Đọc [construction-design-stages](../construction-design-stages/SKILL.md).
   - **Giai đoạn 2 — thi công:** sử dụng/triển khai bản vẽ đã phát hành hoặc cập nhật theo thay đổi tại hiện trường. Đọc [construction-drawing-records](../construction-drawing-records/SKILL.md).
   - **Giai đoạn 3 — hoàn công:** nhận diện yêu cầu, nhưng chưa thực hiện vì quy trình này nằm ngoài phạm vi bộ skill hiện tại.
   - **Chưa rõ hoặc gồm nhiều luồng:** nêu các khả năng và thông tin quyết định cần làm rõ. Trong lúc chờ, có thể kiểm kê tài liệu và phân tích bằng thao tác chỉ đọc. Nếu yêu cầu gồm nhiều luồng, tách sản phẩm và nguồn tài liệu của từng luồng.
3. Lập danh sách đầu vào theo ba nhóm: **đã có**, **còn thiếu nhưng có thể làm bản nháp với giả định ghi rõ**, và **thiếu đến mức chưa thể làm bước được yêu cầu**. Chỉ hỏi tài liệu hoặc quyết định thực sự cản trở công việc mà không thể lấy từ tài liệu hiện có hay kiểm tra an toàn bằng công cụ chỉ đọc. Nói rõ tài liệu đó giúp làm được gì.
4. Nêu giai đoạn và bước đã chọn, sản phẩm sẽ tạo, tài liệu/phiên bản làm căn cứ và việc tiếp theo. Phân loại lại nếu thông tin mới cho thấy sản phẩm khác ban đầu. Không tự cho rằng đã có hồ sơ bước sau chỉ vì đã có hồ sơ bước trước.

## Dấu hiệu nhận diện

| Yêu cầu hoặc tài liệu | Luồng phù hợp | Điều cần xác nhận nếu chưa rõ |
| --- | --- | --- |
| Ý tưởng, quy mô đầu tư, giải pháp chính | Thiết kế cơ sở | Cần phương án để lựa chọn hay hồ sơ làm căn cứ dự án? |
| Tính toán, chọn kích thước hệ thống, chỉ tiêu vật liệu | Thiết kế kỹ thuật | Dùng phiên bản thiết kế cơ sở nào làm căn cứ? |
| Kích thước và chi tiết đủ để xây lắp | Thiết kế bản vẽ thi công | Cần bản vẽ do đơn vị thiết kế phát hành hay bản vẽ triển khai của nhà thầu? |
| Biện pháp, chi tiết lắp đặt/gia công, phối hợp tại công trường | Hồ sơ trong thi công | Bản vẽ được phát hành và điều kiện hiện trường nào làm căn cứ? |
| Sai khác hiện trường, yêu cầu làm rõ, chỉ thị thay đổi | Cập nhật trong thi công | Quyết định hoặc phê duyệt nào cho phép thay đổi? |
| Vị trí/kích thước đã lắp đặt thực tế, hồ sơ bàn giao | Hoàn công — giai đoạn 3 | Xác nhận sản phẩm cần làm là hồ sơ hoàn công; giai đoạn này đang để sau. |

## Giới hạn

- Đây là cách phân luồng, không khẳng định mọi dự án đều bắt buộc có đủ ba bước thiết kế. Dựa vào hợp đồng và quy định áp dụng cho dự án khi đã được cung cấp.
- Người dùng đã xác định ba giai đoạn: thiết kế, thi công, hoàn công. Bộ skill hiện chỉ triển khai hai giai đoạn đầu.
- Có thể phân tích hoặc làm bản nháp với giả định ghi rõ; không phát hành hồ sơ thi công cuối cùng dựa trên giả định chưa kiểm chứng.
- Khi thao tác AutoCAD qua dự án này, dùng thêm `autocad-agent-coordinator`. Skill hiện tại quyết định **đang làm loại hồ sơ nào**; skill AutoCAD hướng dẫn **cách sửa bản vẽ**.
