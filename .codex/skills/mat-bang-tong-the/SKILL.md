---
name: "mat-bang-tong-the"
description: "Dựng hoặc rà soát mặt bằng tổng thể (MBTT) trong AutoCAD cho mọi dự án: đọc brief, chốt phương án khối 3D, nền quy hoạch, ranh đất, chỉ giới, khối nhà, cao độ, kích thước, bảng chỉ tiêu, dàn trang. Dùng khi người dùng nói \"mặt bằng tổng thể\", \"MBTT\", \"tổng mặt bằng\", \"bảng chỉ tiêu\", \"cân bằng đất đai\", \"bản vị trí khu đất\", \"phương án khối\"."
---

# Dựng mặt bằng tổng thể

Mặt bằng tổng thể (MBTT) cho thấy công trình nằm thế nào trong khu đất và bối cảnh quy hoạch: ranh đất, chỉ giới, đường xung quanh, khối nhà, lối tiếp cận, cao độ, cảnh quan và các chỉ tiêu quy hoạch. Skill này áp dụng cho mọi dự án; số liệu ví dụ chỉ để minh họa.

## Quy trình làm việc với người dùng (khi thiết kế phương án)

Khi người dùng nhờ thiết kế phương án và dựng MBTT (không chỉ vẽ lại một MBTT có sẵn), làm theo 7 bước sau. Mỗi bước kết thúc bằng một điểm người dùng có thể xác nhận hoặc sửa.

### Bước 1 – Đọc brief và xác nhận đầu vào
1. Đọc brief/nhiệm vụ thiết kế và tóm tắt lại cho người dùng xác nhận:
   - chỉ tiêu quy hoạch: mật độ xây dựng, hệ số sử dụng đất, tầng cao, số hầm, chỉ giới;
   - yêu cầu chức năng và tiện ích: hồ bơi, khối đế, sảnh, đỗ xe, số căn...;
   - diện tích lô theo brief, so với diện tích đo trên bản vẽ (ghi cả hai nếu lệch).
2. Tự xác định khu đất trên bản vẽ trước, không hỏi suông:
   - tìm ranh lô theo các nhóm bằng chứng ở mục "Ranh đất" (layer, nhãn, kích thước, diện tích);
   - đo kích thước các cạnh và diện tích;
   - đọc hướng đường thật trên bản vẽ (tên đường, mũi tên bắc): đường chính, đường nội khu, phía giáp lô bên cạnh. Không suy hướng từ mô tả bằng lời hay từ mô hình 3D;
   - đọc chỉ giới xây dựng (khối cao tầng, khối đế) và khoảng lùi.
3. Gửi người dùng ảnh chụp khu đất có đánh dấu ranh, kèm tóm tắt: kích thước, diện tích (so với brief), các cạnh giáp đường/lô nào, chỉ giới. Nhờ người dùng xác nhận khu đất bằng công cụ chọn (`AskUserQuestion` nếu có; ba lựa chọn Đúng / Sai / Đúng một phần), gọi ngay lần đầu, không liệt kê lựa chọn bằng văn bản. Chỉ đi tiếp khi đã được xác nhận.

### Bước 2 – Dựng khối 3D để chốt phương án
4. Dựng 2–3 phương án khối đúng kích thước lấy từ bản vẽ (khoảng lùi, cao tầng, khối đế, tháp, hồ bơi) để người dùng xem trực quan. Dựng bằng mô hình 3D tương tác hiển thị ngay trong khung chat (widget dùng three.js, xoay/phóng to được) nếu phiên có công cụ hiển thị; tọa độ khối lấy theo hệ tọa độ cục bộ của lô để dùng lại cho bản vẽ 2D.
   Mô hình phải **đủ chi tiết để đọc được phương án**, không dừng ở khối hộp trơn một màu. Mức tối thiểu:
   - **Tháp:** vạch ngang đúng từng tầng (số vạch = số tầng thiết kế, bước theo chiều cao tầng); mặt đứng một tông màu, cạnh khối có nét viền mảnh; mái màu sáng hơn kèm các khối tum thang, kỹ thuật, bể nước đúng vị trí lõi.
   - **Đế và hầm:** đế khác màu với tháp, dày đúng số tầng đế; nếu phương án có tầng thoáng hoặc đỡ đế trên cột thì vẽ cột đúng lưới cột, không vẽ cột trang trí. Đường bao hầm vẽ nét mờ dưới nền.
   - **Mái đế (khu tiện ích):** hồ bơi và hồ trẻ em màu xanh có viền bể, sân lát màu khác, ghế tắm nắng, cây, khu thay đồ – WC dạng khối; chỉ vẽ tiện ích có trong phương án.
   - **Nền:** mặt đất, đường xung quanh kèm tên đường, ranh lô bằng nét đỏ, chỉ giới xây dựng nét đứt, mũi tên hướng bắc, lô lân cận dạng khối mờ.
   - **Hiển thị:** có đổ bóng nhẹ hoặc hai mức sáng cho các mặt để thấy khối; bảng chú thích màu (tháp, đế, hồ, cây, ram hầm); mỗi phương án một góc nhìn mặc định cho thấy cả mặt giáp đường chính và mái đế.
   Mức chi tiết là để người dùng đánh giá hình khối, không thay số liệu: mọi kích thước vẫn lấy từ bản vẽ và bước 1, không tự thêm chi tiết làm đổi diện tích, chiều cao hay vị trí khối.
5. Mỗi phương án phải **thực tế và xây được**. Trước khi đưa người dùng xem, tự rà từng phương án theo các nhóm dưới đây; mục nào không đạt thì sửa, mục nào chưa chắc thì ghi vào danh sách cần xác nhận. Danh sách là hướng rà soát, không phải giới hạn: bất cứ gì một kiến trúc sư có kinh nghiệm sẽ thấy vô lý thì cũng là lỗi.
   - **Pháp lý và chỉ tiêu:** khối nằm trong chỉ giới xây dựng tương ứng (cao tầng, đế); đủ khoảng lùi; mật độ, hệ số sử dụng đất, tầng cao, chiều cao không vượt quy hoạch; diện tích tính từ hình, không ước lượng.
   - **Công năng:** mỗi tiện ích có lý do tồn tại và chỉ có một (ví dụ một hồ bơi chính, có thể kèm hồ trẻ em liền kề); tiện ích đặt nơi cư dân tới được thuận tiện; có khu thay đồ – WC – tắm tráng gần hồ; sảnh căn hộ tách khỏi lối thương mại.
   - **Giao thông và tiếp cận:** lối vào chính hướng ra đường phù hợp; sảnh đón xe có chỗ dừng không chắn đường; ram hầm đặt ở cạnh giáp đường, đủ bề rộng và độ dốc theo quy chuẩn, không cắt qua lối người đi; xe chữa cháy tiếp cận được mặt nhà theo quy định.
   - **Kết cấu và thi công:** tháp đặt lên đế với lưới cột liên tục hoặc chuyển tiếp hợp lý; không công-xôn, cầu nối hay hồ treo vượt nhịp lớn bất thường; hồ bơi trên mái đế đặt trên vùng kết cấu chịu được tải nước; hình khối thi công được bằng công nghệ phổ biến.
   - **An toàn và PCCC:** đủ khoảng cách tới công trình lân cận hoặc có giải pháp tường ngăn cháy; tối thiểu hai thang thoát hiểm cho tháp, bố trí xa nhau; lan can, rào chắn đủ cao ở mép sàn, mép hồ; không lối đi nguy hiểm.
   - **Môi trường và tiện nghi:** hướng nắng, gió; hồ và sân có nắng phù hợp; tháp không che khuất hoàn toàn tiện ích; căn hộ có tầm nhìn và thông gió.
   - **Vận hành:** bảo trì được (vệ sinh mặt dựng, hồ, cây xanh); có lối kỹ thuật, rác, giao hàng tách khỏi lối chính.
   Khi thuyết minh phương án cho người dùng, nói ngắn gọn phương án đạt các nhóm trên thế nào và còn điểm nào cần xác nhận, kèm **bảng thuyết minh phương án** ở mục dưới để người dùng hiểu phương án gồm những gì.

   **Bảng thuyết minh phương án** (lập cho từng phương án, đưa cùng mô hình 3D, bằng bảng chứ không viết thành đoạn văn):
   - **Căn hộ:** tổng số căn; số căn theo từng loại (studio, 1PN, 2PN, 3PN, duplex, penthouse...); diện tích từng loại (m², nói rõ tính thông thủy hay tim tường) và khoảng chênh nếu cùng loại có nhiều diện tích.
   - **Theo tầng:** bảng từng nhóm tầng (ví dụ tầng 4–23 điển hình, tầng chuyển tiếp, tầng trên cùng): số căn mỗi tầng, mỗi tầng gồm những loại nào, số tầng thuộc nhóm đó; số căn tổng cộng cộng từ bảng này phải bằng tổng số căn ở trên.
   - **Khu tiện ích:** liệt kê từng khu (hồ bơi, hồ trẻ em, phòng gym, sảnh, khu thương mại, sân chơi, vườn mái, thay đồ – WC...), mỗi khu ghi tầng hoặc cao độ đặt, diện tích, và phục vụ ai; tổng số khu tiện ích.
   - **Các tầng không ở:** hầm (số hầm, chỗ đỗ xe), đế (chức năng từng tầng và diện tích), tầng kỹ thuật, mái.
   - **Đối chiếu:** tổng diện tích sàn căn hộ + hành lang, lõi, tiện ích + đế + hầm phải khớp GFA của phương án; ghi hệ số sử dụng diện tích (diện tích bán/sàn xây dựng) và nêu khoảng chênh nếu có.
   Số căn và diện tích tính từ mặt bằng điển hình đã bố trí hoặc từ brief; nếu chưa bố trí căn hộ mà phải ước theo mô-đun, ghi rõ là ước tính, nêu mô-đun và hệ số dùng, và đưa vào danh sách cần xác nhận. Không đưa số căn hoặc diện tích không có căn cứ.
6. Người dùng góp ý, chỉnh trên 3D cho tới khi chốt. Không chuyển sang 2D khi chưa chốt.
7. Ghi lại số liệu đã chốt cho từng phương án (tọa độ khối theo hệ tọa độ cục bộ của lô, số tầng, cao độ, diện tích, GFA, mật độ, FAR) và **bảng thuyết minh phương án** (số căn, loại và diện tích căn hộ, số căn mỗi tầng, danh sách khu tiện ích) để vẽ 2D dùng lại, không đo lại.

### Bước 3 – Chuẩn bị nền 2D
8. Hỏi người dùng trước khi chép, vì câu trả lời quyết định cách dựng:
   - **Phạm vi chép:** chỉ ranh lô (và chỉ giới), hay toàn bộ nền bản vẽ gốc (đường, lô lân cận, ghi chú...).
   - **Cách tổ chức bản vẽ:** mỗi phương án một bản vẽ (file) mới, hay gộp chung các phương án vào một bản vẽ (đặt cạnh nhau với khoảng dời cố định); và đặt trong file hiện tại hay file mới.
   Nếu người dùng chọn chép toàn bộ, liệt kê các nhóm đối tượng thuộc phương án cũ hoặc chi tiết hạ tầng có thể không cần (đèn đường, kích thước cũ, cao độ cũ, nhãn vạt góc, ký hiệu tim đường, mũi tên, hatch ngoài lô, block ram/cổng cũ, vạch lẻ, chữ lỗi font) và hỏi có bỏ không.
9. Chép theo lựa chọn đã chốt; ghi lại handle đối tượng gốc để sau còn lọc hoặc xóa trong bản chép.
10. Tạo layer riêng có tiền tố chung (ví dụ `MBTT-PA-`) cho từng nhóm: hầm, đế, tháp, hồ bơi, cảnh quan, giao thông, tiện ích, cao độ, chữ.

### Bước 4 – Dựng hình 2D
11. Vẽ theo số liệu đã chốt ở bước 2: đường bao tầng hầm (nét đứt/màu nhạt), khối đế, tháp, lõi thang, thang thoát hiểm, hồ bơi và hồ trẻ em, ghế tắm nắng, khu thay đồ – WC, cây xanh, ram hầm (ghi độ dốc, bề rộng), lối vào, sảnh.

### Bước 5 – Ghi chú
12. Ghi tên khu chức năng, cao độ (±0.000 / sàn mái hồ / mái tháp / tum), tên đường, hướng bắc, lô lân cận.
13. Tên bản vẽ có tỉ lệ; cỡ chữ sao cho dòng tiêu đề không dài quá bề ngang lô và không đè sang bản bên cạnh.
14. Bảng chỉ tiêu dưới mỗi bản: diện tích lô, diện tích xây dựng, mật độ, tổng sàn, hệ số sử dụng đất, tầng cao, hầm; kèm giá trị quy hoạch để so. Bên cạnh là bảng căn hộ và tiện ích lấy từ bảng thuyết minh phương án: tổng số căn, số căn và diện tích từng loại, số căn mỗi nhóm tầng, danh sách khu tiện ích kèm diện tích.

### Bước 6 – Kích thước
15. Ghi kích thước theo phương án mới:
    - cạnh tiếp giáp đường chính: khoảng lùi – bề rộng khối – khoảng lùi, kèm tổng;
    - cạnh dọc lô: các đoạn từ ranh tới khối/tháp/sân, kèm tổng chiều dài lô.
16. Trên AutoCAD LT, khi tool không tạo được dimension, vẽ kích thước bằng nét (đường kích thước, đường gióng, gạch 45°) và chữ trên layer kích thước; báo người dùng là không liên kết, sửa hình phải sửa tay.

### Bước 7 – Kiểm tra và bàn giao
17. Chụp màn hình kiểm tra: chữ không đè nhau, không còn chi tiết thừa, số kích thước khớp hình, chữ đúng layer.
18. Đối chiếu từng phương án với brief: chỉ tiêu nào đạt, chỉ tiêu nào chưa đạt hoặc còn giả định.
19. Gửi ảnh và danh sách **cần xác nhận**: diện tích lô, chỉ giới, PCCC, vị trí và độ dốc ram, các giả định khác.
20. Nhắc người dùng lưu file (Ctrl+S) nếu tool không lưu được, kể cả các file khác đã sửa trong phiên.

## Khi chỉ dựng hoặc rà soát MBTT đã có phương án

Không cần chốt phương án 3D (bước 1–2 ở trên) khi người dùng đã có phương án, hoặc chỉ nhờ vẽ lại/rà soát một MBTT. Làm theo trình tự:

1. Kiểm tra căn cứ và bản vẽ nền; xác nhận đơn vị, tỉ lệ, khổ giấy.
2. Xác định và xác nhận ranh đất, chỉ giới với người dùng.
3. Đặt khối công trình vào đúng vị trí; chèn khối lô lân cận dạng block làm bối cảnh.
4. Kiểm tra từng khối nằm trong chỉ giới xây dựng tương ứng và đủ khoảng lùi.
5. Thêm lối tiếp cận, giao thông nội bộ, thoát nước, cảnh quan.
6. Gắn cao độ đường, sân và cao độ mái từng khối.
7. Ghi kích thước pháp lý và định vị; ghi nhãn tên đường, lô, chỉ giới.
8. Lập bảng chỉ tiêu và chú giải; tính lại diện tích từ hình vẽ.
9. Dàn trang: khung tên, viewport, tiêu đề, tỉ lệ, hướng bắc.
10. Kiểm tra cuối: số liệu bảng khớp hình đo và hồ sơ duyệt; khối nhà trong chỉ giới; chữ đúng cỡ; nét đúng layer; không còn đối tượng trùng.

## Trước khi làm

1. Nếu MCP AutoCAD có tool `skills`, nạp `autocad-agent-coordinator` trước và làm theo; nạp thêm các skill nó chỉ định cho ranh đất, chỉ giới và bắt đầu bản vẽ.
2. Xác định: dựng MBTT cho **một lô** hay **nhiều lô/cả khu**; giai đoạn hồ sơ (ý tưởng, TKCS, TKKT, BVTC); tỉ lệ in; khổ giấy.
3. Thu đủ căn cứ: brief/nhiệm vụ thiết kế, bản đồ quy hoạch chi tiết 1/500 hoặc chứng chỉ quy hoạch, bản đồ địa hình/hiện trạng, mặt bằng công trình (tầng 1 và/hoặc mái), cao độ quy hoạch, số quyết định phê duyệt. Thiếu căn cứ quyết định hình vẽ thì hỏi trước.
4. Đọc bản vẽ đang mở: đơn vị (thường là mm), hệ tọa độ, quy ước layer và màu đang dùng. Theo quy ước của bản vẽ; chỉ đề xuất quy ước mới khi bản vẽ trống hoặc người dùng yêu cầu.

## Nguyên tắc cốt lõi

**Tách nền và thiết kế.**
- **Nền quy hoạch và hiện trạng** để thành một block hoặc xref riêng, không sửa khi thiết kế: ranh lô, chỉ giới đường đỏ, chỉ giới xây dựng, tim đường, mép đường và bó vỉa, vạt góc, tên đường, lô lân cận, công trình hiện hữu.
- **Công trình** chồng lên nền. Khi làm nhiều bản (MBTT chung và MBTT từng lô), dùng lại cùng một nền; khối của lô khác chèn vào dạng block làm bối cảnh, không vẽ lại.
- Nên có một **bản vị trí khu đất** chỉ chứa nền, làm điểm xuất phát cho các bản MBTT.
- Khi so sánh nhiều phương án, đặt các bản cạnh nhau với cùng một khoảng dời cố định (ví dụ +100 m mỗi bản) và dùng chung hệ tọa độ cục bộ của lô, để số liệu một phương án áp được cho bản vẽ bằng một phép cộng.

**Một nguồn số liệu.** Diện tích, mật độ, FAR trong bảng chỉ tiêu phải khớp với hình đo được trên bản vẽ, với số liệu đã chốt ở bước 3D, và với hồ sơ quy hoạch được duyệt.

**Thiết kế thực tế.** Mọi phương án phải xây được và vận hành được; một phương án lạ mắt nhưng phi thực tế là phương án sai.

## Ranh đất

- Phân biệt rõ các loại ranh, vì một lô có thể có nhiều ranh đúng cho mục đích khác nhau:
  - **toàn lô quy hoạch** (có thể gồm đường nội bộ, cây xanh, vạt góc);
  - **đất xây dựng công trình** (phần dùng tính mật độ, FAR);
  - chỉ giới đường đỏ, chỉ giới xây dựng (có thể khác nhau cho khối cao tầng và khối thấp tầng/đế).
- Bằng chứng nhận diện: layer ranh (ví dụ `A-SITE-PROP`, `A-FLOR-OTLN`, `000-Property line`), nhãn "RANH GIỚI LÔ ĐẤT", kích thước tổng các cạnh, nhãn vạt góc, diện tích khớp bảng chỉ tiêu. Cần ít nhất hai nhóm bằng chứng độc lập.
- Ranh xuất từ Revit thường là block; trên AutoCAD LT có thể không đọc được nét bên trong, khi đó đối chiếu khung bao block với dim, nhãn và tường trùng mép, và nói rõ là suy luận.
- Luôn xác nhận với người dùng ranh nào được dùng trước khi đặt khối nhà hoặc tính chỉ tiêu.

## Thứ tự lớp thông tin trên MBTT

1. **Bối cảnh:** đường xung quanh (tên, lộ giới, tim đường, bán kính bó vỉa), lô lân cận và công trình hiện hữu (ghi rõ "công trình đã hoàn thành", "đất trống"...), hướng bắc.
2. **Pháp lý:** ranh lô có nhãn đặt ngay trên đường; chỉ giới đường đỏ; chỉ giới xây dựng từng loại, mỗi đường một kiểu nét và có nhãn; vạt góc có nhãn kích thước.
3. **Công trình:** đường bao khối nhà (thường dùng mặt bằng mái hoặc hình chiếu bằng, phân biệt tháp và đế), đường bao tầng hầm, lối vào chính, lối xe và ram hầm, barrier, cầu thang và dốc ngoài nhà, sân, rãnh và ga thoát nước.
4. **Cảnh quan:** cây xanh, mảng xanh, mặt nước/hồ bơi, tiện ích ngoài trời, hatch vật liệu sân. Dùng block có sẵn thay vì vẽ tay.

Chỉ đưa lên MBTT phương án những gì phục vụ đọc phương án; chi tiết kỹ thuật hạ tầng (đèn đường, ga, vạch sơn) bỏ trừ khi người dùng cần.

## Cao độ

- Ghi cao độ mặt đường, vỉa hè, sân hoàn thiện theo cao độ quy hoạch hoặc hệ cao độ dự án (nói rõ hệ nào).
- Gắn cao độ mái/sàn trên cùng (FFL) cho từng khối, để đọc được chiều cao khối ngay trên mặt bằng.
- Cao độ lối vào và đầu/cuối ram dốc nếu có.

## Kích thước

MBTT ghi kích thước pháp lý và định vị, không ghi chi tiết công trình:
- các cạnh ranh lô và chia đoạn (kể cả vạt góc);
- mặt cắt đường: lòng đường, vỉa hè, lộ giới;
- khoảng lùi từ ranh/chỉ giới đường đỏ tới chỉ giới xây dựng và tới khối nhà (riêng khối cao tầng, khối thấp tầng);
- kích thước tổng của khối nhà và khoảng cách giữa các khối/công trình lân cận khi liên quan PCCC hoặc quy chuẩn.

Kích thước chép từ bản gốc mô tả phương án cũ; khi dựng phương án mới thì xóa và ghi lại theo hình mới.

## Bảng chỉ tiêu và chú giải

Vẽ ở vùng riêng trong Model Space (cách xa mặt bằng) rồi lấy ra giấy bằng viewport riêng, hoặc vẽ trực tiếp trên Layout theo quy ước văn phòng. Khi so sánh phương án, mỗi bản có bảng chỉ tiêu riêng ngay dưới hình.
- **Bảng cân bằng đất đai:** diện tích từng lô (gồm và không gồm vạt góc), đất xây dựng công trình, đường nội bộ, cây xanh, sân bãi, tỉ lệ %, số quyết định căn cứ.
- **Bảng chỉ tiêu xây dựng:** diện tích đất, diện tích xây dựng, tổng diện tích sàn (GFA, nói rõ có kể hầm không), mật độ xây dựng, hệ số sử dụng đất (FAR), tầng cao, dân số, chỗ đỗ xe; cột "theo quy hoạch được duyệt" đặt cạnh cột "thiết kế".
- **Chú giải nét:** ranh lô, chỉ giới đường đỏ, từng loại chỉ giới xây dựng, tim đường, và các ký hiệu khác dùng trên bản vẽ.

## Dàn trang và tỉ lệ

- Khung tên theo mẫu của văn phòng/dự án; ghi mã dự án, lô, số bản vẽ, tên bản vẽ, ngày, giai đoạn.
- Viewport chính cho mặt bằng; viewport riêng cho bảng chỉ tiêu, chú giải, sơ đồ vị trí/key plan. Viewport để trên layer không in.
- Tiêu đề hình: số hình, tên "MẶT BẰNG TỔNG THỂ", tên phương án, tỉ lệ.
- Tỉ lệ thường dùng: cả khu/nhiều lô 1:400–1:1000; một lô 1:100–1:300 (chọn sao cho khối nhà đọc rõ và vừa khổ giấy). Có thể xoay khung nhìn để công trình nằm ngang, nhưng giữ đúng hướng bắc.
- Chiều cao chữ trong Model = cỡ chữ in (mm) × mẫu số tỉ lệ. Ví dụ chữ 2 mm ở 1:400 cao 800; ở 1:300 cao 600. Hoặc dùng annotative.

## Ghi chú khi làm qua MCP AutoCAD LT

- Kiểm tra trước tool nào chạy được trên LT; LT thường không cho tạo bản vẽ mới, lưu file, zoom extents hay tạo dimension qua tool. Báo người dùng các giới hạn này và nhắc họ tự lưu.
- Chép nền giữa các vùng: chép theo lô tối đa số đối tượng tool cho phép mỗi lần; ghi lại handle gốc để sau còn lọc và xóa chi tiết thừa trong bản chép.
- Hình học: tạo hàng loạt bằng polyline/circle trong một lệnh batch; tính tọa độ bằng script từ hệ tọa độ cục bộ của lô.
- Chữ: nếu MTEXT bị lỗi, dùng TEXT một dòng (căn giữa tại tọa độ cho trước), mỗi dòng một lệnh, giữ trọn một nhãn tiếng Việt trong một đối tượng; chữ dọc dùng rotation 90.
- Mỗi lệnh sửa cần đúng revision; khi một lệnh bị treo hoặc hết thời gian, kiểm tra bằng cách đọc lại handle hoặc gửi lại với cùng revision trước khi tạo tiếp, tránh tạo trùng.
- Khi sửa nhầm một đối tượng (ví dụ scale nhầm handle), đảo lại phép biến đổi ngay rồi làm lại đúng đối tượng; luôn đọc lại đối tượng sau khi biến đổi.
- Kiểm tra bằng ảnh chụp màn hình sau mỗi đợt lớn (hình học, chữ, kích thước, dọn nền).

## Lỗi thường gặp cần tránh

- Suy hướng đường/hướng bắc từ lời mô tả thay vì đọc trên bản vẽ.
- Chép nguyên nền gốc rồi để lại đèn đường, kích thước và cao độ của phương án cũ.
- Tiêu đề quá dài, chữ đè sang bản vẽ bên cạnh.
- Bản vẽ xuất từ Revit làm chữ tiếng Việt vỡ thành từng mảnh. Khi dựng hoặc sửa trong CAD, mỗi nhãn là một đối tượng chữ liền.
- Trộn font cũ (VNI, TCVN3) với Unicode. Dùng một font Unicode thống nhất.
- Layer trùng lặp đuôi `-1`, `-2` sau nhiều lần chèn/xuất; block ranh xuất trùng. Purge và gộp trước khi phát hành.
- Lấy khung bao (bounding box) làm ranh hoặc đường bao nhà; nhầm ranh toàn lô với ranh đất xây dựng.
- Ghi số liệu bảng chỉ tiêu bằng tay mà không đo lại từ hình.
- Đưa ra phương án phi thực tế (hai hồ bơi vô lý, cầu hồ bơi, kết cấu khó thi công).
