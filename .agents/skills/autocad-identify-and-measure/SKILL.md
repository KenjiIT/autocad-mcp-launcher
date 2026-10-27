---
name: autocad-identify-and-measure
description: Nhận diện trong bản vẽ AutoCAD và đo khi được yêu cầu. Gồm hai việc cùng một nền: (1) ranh khu đất và đường bao khối tòa nhà, phân biệt ranh đất với tường ngoài, mép sàn, mái; (2) vật thể cụ thể như cột, tường, dầm, cửa, kể cả phần bị che khuất, và kích thước của chúng. Dùng trước khi đo, chép, vẽ tiếp hoặc sửa.
---

# Nhận diện và đo trong bản vẽ AutoCAD

Skill này gom hai quy trình nhận diện. Chọn theo câu hỏi của người dùng, đọc tệp tham chiếu tương ứng rồi làm theo; cần cả hai thì đọc cả hai (thường xác định khối nhà trước, rồi nhận diện vật thể trong khối đó).

| Người dùng hỏi | Đọc |
|---|---|
| Ranh khu đất, đường bao khối nhà, tường ngoài hay mép sàn hay mái, chọn đúng khối/tầng trước khi đo, chép hay vẽ tiếp | [references/boundaries.md](references/boundaries.md) |
| Một cột, tường, dầm, cửa hay cụm vật thể; phần bị che khuất; kích thước, khoảng cách, diện tích; tạo vật thể giống vật thể có sẵn | [references/objects-and-measure.md](references/objects-and-measure.md) |

## Nguyên tắc chung cho cả hai

- **Đúng bản vẽ trước.** Xác nhận DWG đang hoạt động, Model hay Layout, tầng/khu vực và đơn vị. Handle chỉ có nghĩa trong DWG đang xét; không tái dùng handle, tọa độ hay kết quả của bản vẽ khác.
- **Đọc đủ dữ liệu.** Kết quả bị cắt, chỉ là mẫu hoặc `changed_only` không đủ chứng minh một thứ không tồn tại. Lấy đủ phạm vi trước khi kết luận và ghi rõ độ phủ.
- **Không kết luận chỉ từ màu hay tên layer.** Đối chiếu hình học thực, ký hiệu, ghi chú và quan hệ không gian. Với block và xref, tính điểm chèn, tỷ lệ và góc quay.
- **Bounding box chỉ để khoanh vùng,** không làm ranh hay kích thước chính xác khi đường bao đầy đủ chưa được xác minh.
- **Mức kết luận** gồm đã xác minh, suy ra có căn cứ, chưa đủ căn cứ (ranh đất dùng cao, vừa, thấp), luôn kèm lý do. Phân biệt quan sát được, suy luận và người dùng đã xác nhận.
- **Chỉ đọc khi được yêu cầu nhận diện hoặc đo.** Chỉ sửa, xóa hay chép khi người dùng giao việc đó. Với MCP AutoCAD, theo `autocad-agent-coordinator` để chọn kết nối và báo cách làm.
- **Ảnh hỗ trợ nhận biết, không thay số đo CAD** khi dữ liệu hình học truy cập được.
