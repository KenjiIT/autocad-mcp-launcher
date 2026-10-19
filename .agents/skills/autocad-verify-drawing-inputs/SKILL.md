---
name: autocad-verify-drawing-inputs
description: Kiểm tra hồ sơ, số liệu, phiên bản và bản vẽ nền đã đủ căn cứ trước khi agent tạo hoặc sửa bản vẽ xây dựng CAD hay chưa. Dùng trước khi dựng mới, triển khai từ hồ sơ thiết kế hoặc sửa theo tài liệu đầu vào; không dùng thay cho thẩm định thiết kế.
---

# Kiểm tra đầu vào trước khi vẽ

Xác định liệu agent có đủ căn cứ để bắt đầu đúng phần việc được giao. Kiểm tra có chọn lọc theo loại bản vẽ và giai đoạn; không yêu cầu mọi tài liệu của toàn dự án cho một bản vẽ nhỏ. Kết quả là trạng thái sẵn sàng, danh sách căn cứ và các điểm cần quyết định. Skill này không tự xác nhận thiết kế tuân thủ quy định và không tạo thêm chức năng MCP.

Khi làm qua AutoCAD, đọc [autocad-agent-coordinator](../autocad-agent-coordinator/SKILL.md) để chọn backend và dùng đúng tool. Trước khi dựng bản vẽ mới, tiếp tục với [autocad-start-construction-drawing](../autocad-start-construction-drawing/SKILL.md). Nếu cần khoanh ranh khu đất/khối nhà, dùng [autocad-identify-boundaries](../autocad-identify-boundaries/SKILL.md). Nếu yêu cầu thuộc một giai đoạn thiết kế cụ thể, dùng [construction-design-stages](../construction-design-stages/SKILL.md).

## 1. Chốt chính xác phần việc

Ghi nhận bản vẽ cần tạo/sửa, dự án, khu vực/tầng, bộ môn, giai đoạn hồ sơ, mục đích sử dụng, đầu ra và mức chi tiết. Phân biệt thiết kế cơ sở, thiết kế kỹ thuật, bản vẽ thi công, bản vẽ triển khai của nhà thầu và bản vẽ hiện trạng/hoàn công. Nếu yêu cầu chỉ nói “vẽ bản vẽ” mà loại bản vẽ hoặc phạm vi làm thay đổi đáng kể căn cứ đầu vào, hỏi làm rõ phần đó trước.

Thông báo ngắn cho người dùng: “Tôi sẽ kiểm tra tài liệu đúng phiên bản, kích thước và thông tin bản vẽ nền trước; sau đó báo phần nào có thể bắt đầu và phần nào còn cần xác nhận.” Kiểm tra này chỉ đọc dữ liệu, chưa sửa bản vẽ.

## 2. Rà soát căn cứ theo loại bản vẽ

Kiểm tra những nhóm sau khi chúng có liên quan đến phần việc. Ghi tên tệp/tờ, đơn vị phát hành hoặc người cung cấp, ngày/phiên bản và trạng thái duyệt nếu có.

| Nhóm căn cứ | Cần đối chiếu |
|---|---|
| Nhiệm vụ thiết kế | Loại công trình, công năng, quy mô, khu vực, yêu cầu chủ đầu tư và sản phẩm cần bàn giao |
| Hồ sơ thiết kế | Bản vẽ nền và thuyết minh đúng bộ môn, tầng/khu vực, giai đoạn và phiên bản; nhận biết nội dung đã chọn với phương án còn xem xét |
| Khu đất / tổng mặt bằng | Khảo sát địa hình, ranh và tọa độ, cao độ, hướng, hiện trạng; căn cứ quy hoạch/chỉ giới và các giới hạn áp dụng |
| Kiến trúc | Công năng, kích thước, trục, cao độ, tường/cửa và quan hệ giữa các tầng theo phạm vi cần vẽ |
| Kết cấu | Lưới trục/cột, hệ chịu lực, kích thước cấu kiện hoặc nguyên tắc đã được giao cho giai đoạn hiện tại |
| MEP và hạ tầng | Điểm đấu nối, tuyến chính, phòng kỹ thuật, trục/hộp kỹ thuật và khoảng không cần phối hợp |
| PCCC và tiếp cận | Phân loại công năng/quy mô và căn cứ quy chuẩn, phương án lối tiếp cận/thoát nạn liên quan đến bản vẽ |
| Nền bản vẽ CAD | DWG/DXF hoặc tệp nền tương ứng, đơn vị, hệ tọa độ/mốc cao độ, Model/Layout, xref, layer, block và quy ước trình bày |

Không yêu cầu bảng trên đầy đủ nếu một nhóm không ảnh hưởng tới bản vẽ. Ví dụ, địa chất thường là căn cứ cần thiết khi phạm vi gồm móng/tầng hầm; không mặc định nó là điều kiện chặn để chỉ bố trí sơ bộ đường đi trên tổng mặt bằng.

## 3. Kiểm tra nguồn, phiên bản và tính nhất quán

- Ưu tiên hồ sơ được duyệt hoặc được chỉ định làm căn cứ, khảo sát có thông tin nguồn, văn bản quy hoạch/thoả thuận đang áp dụng và quyết định của người có thẩm quyền trong dự án.
- So tên dự án, vị trí, tầng, bộ môn, mã bản vẽ, ngày phát hành, revision và trạng thái. Không coi tệp mới nhất theo ngày lưu là tệp có thẩm quyền cao nhất.
- Đối chiếu các kích thước/định vị chính giữa tài liệu liên quan: ranh và trục, cao độ và mốc, vị trí khối nhà và đường vào, hệ trục giữa tầng và bộ môn. Ghi cụ thể từng xung đột, không tự chọn một số liệu thuận tiện.
- Xác nhận đơn vị và hệ tọa độ/mốc cao độ trước khi ghép nguồn. Không dùng phép đo trên ảnh/PDF làm kích thước chính xác trừ khi có tỷ lệ đáng tin cậy và kích thước kiểm soát để hiệu chuẩn; ảnh chụp phối cảnh không phải bản đo.
- Khi viện dẫn quy chuẩn/pháp luật, kiểm tra nguồn chính thức, phạm vi áp dụng và ngày hiệu lực theo dự án. Tách yêu cầu bắt buộc khỏi tiêu chuẩn được dự án chọn và hướng dẫn nội bộ. Nêu nguồn/ngày khi đã thực sự tra cứu; không nói đã kiểm tra nếu chỉ dựa vào trí nhớ.
- Nếu đã có DWG đang mở, xác nhận đúng đường dẫn/tên, bản vẽ hoạt động, đơn vị, hướng/hệ tọa độ khi có, xref và trạng thái lưu. Handle đối tượng chỉ có ý nghĩa trong đúng bản vẽ và phiên bản đã kiểm tra.

## 4. Phân loại thiếu sót và kết luận sẵn sàng

Phân loại từng điểm còn thiếu:

- **Chặn phần việc:** thiếu hoặc xung đột dữ liệu làm thay đổi vị trí, kích thước, cao độ, công năng hoặc đối tượng cần sửa; ví dụ chưa xác định đúng DWG đích, hệ đơn vị không rõ khi phải đặt tọa độ, hai phiên bản căn cứ cho kích thước khác nhau, hoặc thiếu ranh/định vị cho bản vẽ tổng mặt bằng chính xác.
- **Có thể làm song song:** không ngăn phần hình học độc lập đã có đủ căn cứ, nhưng phải được giải quyết trước khi phần phụ thuộc được chốt. Tách phần này khỏi vùng đã xác minh và không trình bày như dữ liệu cuối cùng.
- **Giả định chấp nhận được cho phương án:** có thể đề xuất tạm thời nếu người dùng muốn phương án khái niệm. Ghi giá trị/ranh giả định, nguồn hoặc lý do, ảnh hưởng và người cần xác nhận. Không biến giả định thành dữ liệu đã duyệt.

Kết luận bằng một trong ba trạng thái:

1. **ĐỦ CĂN CỨ ĐỂ BẮT ĐẦU:** tài liệu và dữ liệu quyết định cho phạm vi hiện tại đã được xác định, không còn xung đột chặn.
2. **BẮT ĐẦU ĐƯỢC CÓ ĐIỀU KIỆN:** có phần độc lập để triển khai; liệt kê giả định/đầu việc đang mở và điểm phải xác nhận trước khi chốt hoặc tiếp tục phần phụ thuộc.
3. **CHƯA ĐỦ CĂN CỨ:** nêu tối đa các câu hỏi then chốt theo thứ tự ảnh hưởng; chờ câu trả lời cho thông tin chặn. Có thể tiếp tục phần chỉ đọc hoặc độc lập không bị ảnh hưởng.

Trả kết quả gọn theo dạng:

| Hạng mục | Trạng thái | Căn cứ đã thấy | Thiếu/xung đột và bước tiếp |
|---|---|---|---|
| Định vị / tệp đích | Đủ / thiếu / xung đột | Tệp, bản vẽ hoặc văn bản | Câu hỏi/hành động |
| Hình học và cao độ | Đủ / thiếu / xung đột | Kích thước/mốc nguồn | Câu hỏi/hành động |
| Quy hoạch và yêu cầu | Đủ / thiếu / xung đột | Tài liệu/version | Câu hỏi/hành động |
| Phối hợp bộ môn | Đủ / thiếu / xung đột | Bản vẽ giao diện | Câu hỏi/hành động |
| Kết luận | Một trong ba trạng thái trên | Phạm vi có thể làm ngay | Giới hạn |

Chỉ hỏi thông tin ảnh hưởng quyết định hiện tại; nhóm các câu hỏi ngắn trong một lượt. Đưa lựa chọn cụ thể khi tài liệu hiện có cho phép. Không hỏi lại điều người dùng đã trả lời và còn hiệu lực.

## 5. Bàn giao sang bước dựng CAD

Khi đủ căn cứ hoặc người dùng cho phép làm phương án có điều kiện, chuyển sang skill phù hợp. Trước thay đổi đầu tiên, thông báo phạm vi và giả định. Dựng đúng giai đoạn: thiết kế cơ sở thể hiện giải pháp và thông số chủ yếu; không tự thêm chi tiết thi công không được yêu cầu. Đọc lại bản vẽ sau thao tác và báo điều đã kiểm tra, phần còn mở, trạng thái lưu/xuất quan sát được.

Không kết luận bản vẽ tuân thủ, đủ phát hành hoặc được phép thi công chỉ vì checklist đã qua. Việc thẩm định, phê duyệt và trách nhiệm nghề nghiệp vẫn thuộc các bên có thẩm quyền của dự án.
