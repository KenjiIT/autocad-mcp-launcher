---
name: autocad-structural-drawing
description: Lập mới hoặc triển khai bản vẽ kết cấu AutoCAD từ nhiệm vụ và hồ sơ thiết kế - kiểm tra đầu vào, nội dung bản vẽ, trình tự dựng hình, ghi chú, phối hợp, kiểm soát trước bàn giao. Dùng khi người dùng nói 'bản vẽ kết cấu', móng, cột, dầm, sàn, kết cấu đứng, mặt cắt, chi tiết kết cấu. Với mặt bằng dầm-sàn-cột một tầng, dùng thêm `autocad-structural-floor-plan`.
---

# Lập bản vẽ kết cấu AutoCAD

Tạo bản vẽ thể hiện trung thực giải pháp kết cấu đã được giao hoặc được người có thẩm quyền xác nhận. Skill này bao quát việc lập và triển khai bản vẽ kết cấu nói chung; không giới hạn ở một dự án, một tầng, hoặc việc dựng lại từ DWG tham chiếu.

Khi thao tác AutoCAD qua MCP, dùng [autocad-agent-coordinator](../autocad-agent-coordinator/SKILL.md) để chọn đúng backend và xác nhận kết quả từ bản vẽ. Khi cần rà soát hồ sơ đầu vào trước khi vẽ, dùng [autocad-verify-drawing-inputs](../autocad-verify-drawing-inputs/SKILL.md). Skill này hướng dẫn quy trình bản vẽ, không thay thế thiết kế, tính toán, thẩm tra hoặc phê duyệt kết cấu.

## 1. Chốt phạm vi và sản phẩm

Trước khi dựng hình, xác định:

- Công trình, khối nhà, tầng/khu vực và hệ kết cấu liên quan.
- Loại bản vẽ cần lập: móng, mặt bằng định vị cột/vách, mặt bằng dầm-sàn, mặt đứng, mặt cắt, chi tiết nút, thống kê cấu kiện/thép, hoặc tổ hợp các loại này.
- Giai đoạn và mục đích: phương án, thiết kế cơ sở, thiết kế kỹ thuật, bản vẽ thi công, điều chỉnh, hay hoàn công.
- Mã tờ, tỷ lệ/khổ giấy nếu đã có, định dạng đầu ra, tệp DWG đích và phạm vi được phép sửa.
- Phần nào đã được thiết kế/chốt và phần nào mới cần thể hiện hoặc đề xuất.

Nếu thiếu thông tin làm thay đổi vị trí, kích thước, cấu tạo hoặc phạm vi phát hành, nêu rõ điểm chặn trước khi vẽ phần phụ thuộc. Có thể triển khai phần độc lập đã đủ căn cứ. Chỉ đưa giả định vào bản vẽ khi người dùng yêu cầu phương án; ghi rõ giả định và trạng thái cần xác nhận.

## 2. Hồ sơ và dữ liệu cần có

Kiểm tra theo phạm vi bản vẽ, không đòi hồ sơ không liên quan. Ghi nguồn, mã bản vẽ/tệp, tầng, ngày/revision và trạng thái phát hành khi có.

| Nhóm dữ liệu | Cần kiểm tra khi liên quan |
|---|---|
| Nhiệm vụ và cơ sở thiết kế | Quy mô, công năng, giai đoạn, hệ kết cấu, vật liệu, tải trọng/yêu cầu thiết kế và quy ước dự án đang áp dụng. |
| Kiến trúc | Mặt bằng đúng tầng và phiên bản; trục, kích thước, cao độ, tường, lõi, cầu thang, khe, lỗ mở và ranh sàn. |
| Thiết kế kết cấu | Thuyết minh, tính toán, mô hình hoặc chỉ dẫn thiết kế đã được chọn; sơ đồ chịu lực; kích thước, cao độ và cấu tạo cấu kiện; bảng thống kê nếu có. |
| Móng và nền đất | Khảo sát địa chất, cao độ nền/mực nước, tải trọng và giải pháp móng đã được thiết kế; chỉ yêu cầu phần cần thiết cho bản vẽ móng/tầng hầm. |
| Phối hợp bộ môn | Lỗ mở, sleeve, ống/hộp kỹ thuật, tải trọng thiết bị, yêu cầu kiến trúc và các vùng cần chừa hoặc tránh. |
| Nền CAD và tiêu chuẩn trình bày | Template, đơn vị, gốc/hướng tọa độ, quy ước layer, kiểu nét, chữ, kích thước, khung tên, CTB/STB và xref. |

Phân loại dữ liệu thành **đã xác nhận**, **suy ra có kiểm soát** và **chưa có căn cứ**. So sánh các nguồn cùng tầng và cùng phiên bản. Không tự chọn một trong hai số liệu mâu thuẫn. Điểm chèn nhãn, tên cấu kiện, ký hiệu trục hoặc số lượng đối tượng không tự tạo ra hình học cấu kiện.

## 3. Xác định nội dung phải thể hiện

Chọn danh mục theo loại tờ và giai đoạn:

- **Mặt bằng kết cấu:** lưới trục và kích thước trục; cột/vách; dầm và mã dầm; đường bao sàn, lỗ mở, khe; cao độ hoặc ký hiệu sàn; mặt cắt/chi tiết tham chiếu; ghi chú phối hợp cần thiết.
- **Móng:** định vị theo trục; loại và kích thước móng/cọc/đài/giằng theo thiết kế; cao độ, cấu tạo, chi tiết và bảng thống kê phù hợp phạm vi.
- **Cột/vách:** vị trí, mã, kích thước/tiết diện theo tầng; thay đổi tiết diện và cao độ; mặt đứng, cấu tạo nối hoặc chi tiết khi được yêu cầu.
- **Dầm/sàn:** sơ đồ và kích thước cấu kiện; cao độ, bậc sàn, lỗ mở; mặt cắt/chi tiết cốt thép và bảng thống kê khi thuộc phạm vi bản vẽ.
- **Chi tiết kết cấu:** kích thước, vật liệu, cấu tạo, mặt cắt, ký hiệu và tham chiếu về vị trí áp dụng. Các yêu cầu cốt thép/neo/nối phải lấy từ thiết kế hoặc tiêu chuẩn được dự án xác định.

Không nhồi mọi nội dung vào một tờ nếu làm mất khả năng đọc. Phân tờ và tỷ lệ theo mức chi tiết cần thể hiện và quy ước dự án.

## 4. Trình tự triển khai

1. **Kiểm tra bản vẽ đích.** Xác nhận đúng tệp, tầng, Model/Layout, đơn vị, tọa độ, hướng, layer, xref và trạng thái lưu. Tạo bản vẽ mới hoặc bản làm việc riêng khi nhiệm vụ yêu cầu; giữ nguyên nguồn được bảo toàn.
2. **Nạp nền và căn chỉnh.** Dùng đúng kiến trúc cùng tầng/phiên bản. Xác nhận gốc tọa độ, hướng, trục và cao độ bằng kích thước hoặc mốc kiểm soát. Không căn chỉ bằng cảm giác hoặc ảnh chụp không hiệu chuẩn. Kiểm tra các tầng có dùng cùng hệ trục hay có dịch chuyển.
3. **Thiết lập bản vẽ.** Dùng template và quy ước dự án nếu có; vẽ hình học theo kích thước thật 1:1 trong Model. Tạo hoặc dùng layer theo chức năng, tách kết cấu, nền kiến trúc, trục, chữ, kích thước, hatch và tham chiếu theo quy ước hiện hành. Không tự áp tên/màu mẫu nếu DWG đã có tiêu chuẩn riêng.
4. **Dựng cấu kiện theo căn cứ thiết kế.** Bố trí trục, cột/vách, móng, dầm, sàn và các lỗ mở theo đúng dữ liệu hình học và cao độ. Dùng footprint/đường bao hoặc hai đầu cấu kiện thật; kiểm tra vị trí gối và liên kết. Không suy tiết diện, chiều dài, phương dầm hoặc đường bao lỗ mở từ vị trí/góc xoay nhãn, trục gần nhất hay hình chữ nhật lặp theo ô lưới.
5. **Ghi mã và chú thích sau hình học.** Đặt nhãn cấu kiện lên đúng đối tượng sau khi đã có hình học. Kích thước phải đo từ các điểm hình học thực; không sửa nội dung số đo để che hình học sai. Chỉ ghi cao độ, vật liệu, cấu tạo, tải trọng hoặc thông số có nguồn. Gắn chi tiết/bảng thống kê tới đúng cấu kiện và phạm vi áp dụng.
6. **Phối hợp.** Kiểm tra cột/dầm/vách với kiến trúc; rà lỗ mở và vùng kỹ thuật với MEP; rà cao độ, khe, công-xôn, dầm chuyển và thay đổi hệ kết cấu giữa tầng. Ghi thành vấn đề cần quyết định khi hồ sơ bộ môn xung đột; không tự dịch cấu kiện để làm vừa nền.
7. **Bố trí tờ và xuất bản.** Tạo Layout, khung tên, viewport, tỷ lệ, nét in và bảng plot theo hồ sơ dự án. Chọn tỷ lệ đủ đọc cho mặt bằng và chi tiết. Kiểm tra preview/PDF trước khi kết luận bản in đạt; DWG lưu thành công không đồng nghĩa tờ in đã đúng.

## 5. Tự kiểm soát chất lượng

Kiểm tra bản vẽ thực tế sau từng nhóm thay đổi và trước bàn giao:

- **Định vị:** trục, khoảng cách trục, tọa độ, mốc cao độ và hướng nhất quán với căn cứ.
- **Tính đầy đủ:** các cấu kiện và ký hiệu thuộc phạm vi đều có; từng mã nhãn gắn với đối tượng phù hợp; không dùng tổng số entity làm bằng chứng đủ cấu kiện.
- **Hình học và liên kết:** kích thước/footprint đúng; dầm có đầu và gối hợp lý theo thiết kế; cột/vách đặt đúng; lỗ mở có ranh thực và không bị cấu kiện giả cắt ngang; không có đoạn rời, trùng hoặc lặp theo suy đoán.
- **Kích thước và chú thích:** số đo lấy từ hình học; đơn vị, cao độ, mã và tham chiếu chi tiết không mâu thuẫn; chữ không rơi khỏi vùng hoặc che cấu kiện.
- **CAD và bản in:** layer, ByLayer, kiểu nét, tỷ lệ, khung tên, xref, hatch và font hiển thị; kiểm tra đối tượng thừa/ngoài phạm vi; chạy AUDIT nếu AutoCAD hỗ trợ; mở lại hoặc đọc lại tệp đã lưu và xem bản preview/PDF.

Tách kết quả theo trạng thái **đã xác minh**, **cần xác nhận** và **chưa kiểm được**. Chỉ báo “đã hoàn tất bản vẽ” khi phạm vi, hình học, nội dung tờ và đầu ra đã được kiểm tra. Không tuyên bố bản vẽ đủ điều kiện thi công, tuân thủ hoặc đã được thẩm định chỉ dựa trên thao tác CAD hay checklist.

## 6. Bàn giao

Bàn giao tệp và mã/revision; nêu loại tờ, tầng, đơn vị, nguồn chính đã dùng, phần đã triển khai, kiểm tra đã thực hiện và các điểm còn chờ quyết định. Nếu xuất PDF/preview, ghi rõ tệp và kết quả thực tế. Không gọi một phương án sơ bộ là bản phát hành cuối.
