---
name: autocad-agent-coordinator
description: Điều phối công việc AutoCAD qua hai MCP autocad_beiming và autocad_puran của dự án. Dùng khi agent cần kiểm tra, tạo, sửa hoặc xuất bản vẽ CAD; thông báo cách làm trước khi sửa và kiểm tra kết quả sau khi thao tác.
---

# Điều phối agent làm việc với AutoCAD

Dùng quy trình này cho công việc AutoCAD thực hiện qua ứng dụng kết nối MCP của dự án. Skill hướng dẫn agent; các công cụ MCP mới thực hiện thao tác CAD. Không nói rằng việc nạp skill đã mở AutoCAD hoặc kết nối MCP.

## Nhận diện ranh đất và khối nhà

Khi cần xác định ranh khu đất, chọn khối tòa nhà, phân biệt tường ngoài/mép sàn/mái hoặc khoanh phạm vi trước khi đo, chép hay vẽ tiếp, đọc và áp dụng [autocad-identify-boundaries](../autocad-identify-boundaries/SKILL.md) nếu skill có trong môi trường agent.

Ưu tiên tìm ranh đất rồi lấy toàn bộ đối tượng bên trong làm tập ứng viên; giữ riêng đối tượng chạm/cắt ranh, sau đó lọc hoặc nhờ người dùng xác nhận nhóm thuộc tòa nhà. Nếu chưa tìm được ranh, hỏi màu, layer, vị trí hoặc đối tượng mẫu. Tập ứng viên trong ranh có thể chứa sân, đường và ghi chú; chưa coi tất cả là đường bao nhà đã xác minh. Kiểm tra đúng DWG và phạm vi trước khi tái dùng kết quả nhận diện.

Nếu skill chưa được cài, áp dụng quy trình tóm tắt trên bằng các tool thực tế đang có và nói rõ điểm chưa xác định. Skill nhận diện không tự bổ sung tool MCP; chỉ sửa/chép khi nằm trong yêu cầu của người dùng.

## Bắt đầu bản vẽ xây dựng

Trước khi tạo hoặc sửa bản vẽ theo hồ sơ đầu vào, đọc và áp dụng [autocad-verify-drawing-inputs](../autocad-verify-drawing-inputs/SKILL.md) để kiểm tra đúng phiên bản, đơn vị, định vị và các dữ liệu còn thiếu. Nếu có thông tin chặn, hỏi rõ trước phần phụ thuộc; nếu chỉ còn giả định cho phương án sơ bộ, nêu chúng cho người dùng.

Khi người dùng muốn tạo mặt bằng hoặc bắt đầu dựng bản vẽ xây dựng 2D từ căn cứ thiết kế, đọc và áp dụng [autocad-start-construction-drawing](../autocad-start-construction-drawing/SKILL.md) nếu skill có trong môi trường agent. Skill này hướng dẫn kiểm tra đầu vào, đơn vị, layer, hệ trục, hình học, chữ/kích thước và tờ in trước khi kết luận hoàn thành. Nếu skill chưa được cài, giữ trình tự đó và dùng các tool MCP thực tế đang có.

## Quy trình

1. Xác định kết quả người dùng cần, bản vẽ sẽ tác động và bộ môn của công việc. Dùng công cụ chỉ đọc để kiểm tra các MCP sẵn có và trạng thái bản vẽ hiện tại. Với bản vẽ xây dựng như kiến trúc, kết cấu, dùng `autocad_beiming`. Chỉ dùng `autocad_puran` cho bản vẽ MEP như điện, điều hòa, cấp thoát nước và các hệ kỹ thuật liên quan. Nếu yêu cầu gồm cả xây dựng và MEP, tách phần việc theo bộ môn rồi chọn MCP tương ứng cho từng phần. Gateway sẽ đổi kết nối khi gọi công cụ. Thử AutoCAD trước; nếu công cụ trả `AUTOCAD_UNAVAILABLE`, hỏi người dùng: “AutoCAD hiện không chạy. Bạn có muốn tôi xuất bản vẽ dạng DXF thay thế không?” Chờ câu trả lời rõ ràng; chỉ khi được đồng ý mới gọi `launcher_set_backend` với `mode="ezdxf", user_confirmed=true`. Nếu người dùng không đồng ý, dừng thao tác và chờ AutoCAD.
2. Trước thao tác đầu tiên làm thay đổi bản vẽ, thông báo ngắn gọn cho người dùng: bản vẽ hoặc khu vực nào sẽ thay đổi, sẽ làm gì và sẽ kiểm tra kết quả ra sao. Nếu công việc có nhiều bước, liệt kê các bước chính. Đây là thông báo cách làm; chỉ hỏi phê duyệt khi nhiệm vụ hoặc môi trường agent thực sự yêu cầu.
3. Thực hiện bằng các công cụ mà MCP đã chọn thực sự cung cấp. Đọc cấu trúc tham số của từng công cụ trước khi gọi. Khi tạo đối tượng, kiểm tra layer và áp dụng quy ước màu của bản vẽ theo mục dưới đây. Thực hiện các thao tác sửa CAD theo thứ tự. Không tự giả định có khả năng giao dịch, hoàn tác, đọc lại hay xuất tệp nếu công cụ hiện dùng không cung cấp. Nếu cách làm thay đổi đáng kể, thông báo trước khi tiếp tục.
4. Sau mỗi thay đổi quan trọng, dùng công cụ chỉ đọc sẵn có để so trạng thái bản vẽ thực tế với yêu cầu. Nếu lệnh lỗi hoặc kết quả không rõ, dừng các bước phụ thuộc, báo lỗi cụ thể và chưa kết luận đã hoàn thành.
5. Kết thúc bằng báo cáo ngắn: đã thay đổi gì, đã kiểm tra gì và điểm nào còn chưa chắc chắn. Phân biệt lệnh chạy thành công với việc đã xác minh bản vẽ đúng yêu cầu.

### Đọc bản vẽ và theo dõi thay đổi

Khi cần nắm cấu trúc bản vẽ qua Beiming, gọi `drawing` với `operation="audit"`; dùng `include_entities=false` nếu chỉ cần tóm tắt. `changed_only=true` trả các đối tượng thay đổi so với lần audit trước của cùng bản vẽ trong cùng tiến trình MCP và cùng phạm vi. Bỏ tùy chọn này nếu cần toàn bộ đối tượng. Khi chuyển sang bản vẽ khác, baseline được tách riêng; sau khi có thay đổi mà kết quả chưa xác nhận được, đọc lại trước khi kết luận.

Với DWG lớn, bắt đầu bằng một lần audit Model Space với `include_entities=false` để lấy tổng số và số lượng theo layer; sau đó chỉ audit các layer ứng viên cần kiểm tra, tuần tự. Không giả định audit theo layer dùng snapshot đã cache: trong cấu hình COM-only hiện tại, Beiming không báo revision từ database event và mỗi audit có thể quét lại Model Space. Audit chỉ trả tối đa 500 entity; nếu có `truncated=true`, mẫu đó chưa đủ để khẳng định đã kiểm tra hết. Tránh gọi `entity.list` hoặc `entity.get` lặp cho hàng trăm đối tượng và không gửi nhiều lệnh đọc CAD song song. Chỉ tái sử dụng cache khi kết quả/cấu hình xác nhận cache hit và đúng bản vẽ, revision.

## Quy ước màu của bản vẽ hiện tại

Áp dụng bảng này khi vẽ hoặc chỉnh sửa **bản vẽ đang dùng quy ước này**. Trước khi tạo đối tượng, đọc layer và màu đang có trong DWG; nếu bản vẽ khác dùng quy ước khác, theo quy ước của bản vẽ đó hoặc hỏi người dùng. Ưu tiên đặt màu đối tượng là `ByLayer` và đặt ACI cho layer tương ứng. Không đổi màu hàng loạt các đối tượng sẵn có chỉ để khớp bảng này. Khi sao chép giữa các DWG, giữ nguyên layer và màu nguồn, trừ khi người dùng yêu cầu chuyển sang quy ước của DWG đích.

| ACI | Màu tham chiếu | Đối tượng / layer |
|---:|---|---|
| 1 | Đỏ `#FF0000` | Tường, đường bao, kính và đố kính, cầu thang, đường dốc, lan can, đường kích thước và số đo. |
| 2 | Vàng `#FFFF00` | Cửa đi, khung cửa, nét biểu diễn cửa mở. |
| 3 | Xanh lá `#00FF00` | Tên phòng, diện tích, cao độ, vòng tròn và chữ/số trục định vị, ký hiệu tham chiếu. |
| 4 | Xanh lơ `#00FFFF` | Cột kết cấu, layer `S-COLS`. |
| 6 | Tím hồng `#FF00FF` | Ranh khu đất, layer `A-SITE-PROP`. |
| 7 | Trắng `#FFFFFF` trên nền tối | Chữ ghi chú, mũi tên, một số hatch và chi tiết phụ. |
| 8 | Xám `#808080` | Đường trục định vị, nội thất, thiết bị vệ sinh, tủ và một số chi tiết cửa. |
| 10 | Đỏ `#FF0000` | Layer `003-wall` đã khai báo; chưa thấy đối tượng trực tiếp trong Model. Chỉ dùng nếu thực sự vẽ trên layer này. |
| 11 | Hồng nhạt `#FF7F7F` | Hatch cột `S-COLS-PATT`; layer hatch tường `A-FLOR-WALL-PATT` cũng khai báo màu này. |

ACI là mã màu cần truyền cho AutoCAD khi công cụ nhận ACI; HEX/RGB chỉ để nhận biết màu. ACI 1 và ACI 10 cùng đỏ trên màn hình nhưng là hai chỉ số khác nhau, có thể in khác nhau theo CTB. ACI 7 đổi cách hiển thị theo nền AutoCAD. Đường trục hình học dùng ACI 8; vòng tròn và chữ/số nhãn trục dùng ACI 3. Với chi tiết cửa có cả ACI 2 và 8, đọc layer và đối tượng cùng loại trong bản vẽ trước khi chọn. Trước khi xuất/in, kiểm tra CTB/STB và bản xem trước; màu hiển thị không quyết định bề rộng nét in.

## Giới hạn

- Việc nạp hoặc gọi skill không chứng minh rằng công cụ đã chạy. Chỉ báo cáo kết quả đã quan sát được.
- Không tự tạo tên thao tác MCP hoặc dùng tham số ví dụ như thể đó là cấu trúc tham số được hỗ trợ.
- Không sửa đối tượng ngoài phạm vi yêu cầu hoặc âm thầm đổi bản vẽ đang hoạt động. Làm rõ bản vẽ đích nếu có thể tác động đến nhiều bản vẽ.
- Không chọn `autocad_puran` cho bản vẽ xây dựng chỉ vì công cụ của nó thuận tiện hơn. Nếu chưa rõ bộ môn, làm rõ hoặc kiểm tra bản vẽ bằng thao tác chỉ đọc trước khi chọn MCP để sửa.
- Backend `ezdxf` chỉ tạo hoặc mở DXF, không tạo DWG. Gọi `drawing.save` để lưu DXF trước khi đổi MCP hoặc quay lại AutoCAD. Khi người dùng muốn quay lại AutoCAD, gọi `launcher_set_backend` với `mode="autocad"` rồi thử tool.
- Với bản vẽ cơ khí theo GB/T, dùng thêm `mechanical-drafting-gbt` nếu agent có skill đó. Các bước kiểm tra kỹ thuật của skill này bổ sung cho quy trình điều phối, không thay thế việc thông báo cách làm cho người dùng.
- Skill yêu cầu agent giải thích trước khi thao tác. Nếu môi trường chạy cần bắt buộc mọi agent tuân theo thứ tự này, môi trường đó cũng phải chặn thao tác sửa CAD ở bên ngoài skill.

## Ví dụ thông báo cách làm

"Tôi sẽ kiểm tra bản vẽ đang mở, tạo các đối tượng theo kích thước bạn đưa trên đúng layer, rồi đọc lại tọa độ và số lượng đối tượng để xác nhận. Nếu bản vẽ hoặc kích thước chưa rõ, tôi sẽ hỏi trước khi sửa."
