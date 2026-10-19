---
name: construction-boundaries-grids
description: Phối hợp chỉ giới đường đỏ, chỉ giới xây dựng, khoảng lùi và hệ trục định vị khi lập hoặc rà soát tổng mặt bằng, mặt bằng tầng và các khối cao tầng/thấp tầng của cùng dự án.
---

# Chỉ giới và hệ trục chung của hồ sơ xây dựng

Dùng skill này khi lập hoặc rà soát tổng mặt bằng, mặt bằng tầng, vị trí khối nhà, khoảng lùi hoặc tính nhất quán của hệ trục giữa các bản vẽ. Kết hợp với `construction-design-stages` để xác định bước hồ sơ. Khi cần quy tắc **ký hiệu** trục hoặc đường nét, đọc [construction-drawing-tcvn5570](../construction-drawing-tcvn5570/SKILL.md).

Đọc [QCVN 01:2021/BXD đóng gói](references/QCVN_01_2021_BXD.pdf), mục 1.4.22-1.4.24 về chỉ giới/khoảng lùi và mục 2.6.2 về khoảng lùi phần đế, tháp. Kiểm tra tình trạng quy chuẩn và quy hoạch áp dụng của dự án khi kết luận tuân thủ; PDF đóng gói là bản để đối chiếu nội dung, không thay cho hồ sơ quy hoạch được duyệt của dự án.

## Căn cứ định vị

**Ranh giới trách nhiệm trước khi vẽ:** Người dùng/người thiết kế cung cấp hoặc xác nhận căn cứ định vị và phương án hệ trục; agent chỉ chuyển dữ liệu đã xác định vào CAD, tính khoảng cách, ghi kích thước và kiểm tra. Với chỉ giới, phải có hồ sơ quy hoạch/giấy phép/tài liệu dự án được duyệt hoặc đường đã được người dùng chỉ rõ là căn cứ. Với trục, phải có bản vẽ trục đã chọn làm căn cứ, tọa độ, kích thước nhịp/mốc/hướng, hoặc vị trí trục được người dùng xác nhận. Có thể lấy trực tiếp tọa độ từ đối tượng CAD đã được xác định rõ là trục/chỉ giới trong đúng bản vẽ và phiên bản; ảnh chụp, màu hoặc layer đơn lẻ không đủ để xác lập tính pháp lý hay vị trí thiết kế. Không tự chia nhịp, đặt tên hoặc dời trục, tự xác định chỉ giới hay khoảng lùi bằng phỏng đoán.

Nếu thiếu hoặc có xung đột ở các căn cứ trên, **không tạo/sửa đối tượng trục, chỉ giới hay kích thước định vị phụ thuộc vào chúng trong CAD**. Chỉ đọc, đo, lập bảng phần đã biết/phần thiếu và nêu đúng dữ liệu cần người dùng xác nhận. Có thể tiếp tục phần bản vẽ độc lập đã đủ căn cứ; đề xuất bố trí trục ở dạng mô tả riêng nếu người dùng yêu cầu, và chỉ đưa phương án đó vào CAD sau khi người dùng chọn/xác nhận. Yêu cầu vẽ chung không đồng nghĩa với việc cho phép agent tự chốt các vị trí còn thiếu.

- Phân biệt **chỉ giới đường đỏ** (ranh quy hoạch giữa đất xây dựng và đất dành cho giao thông/hạ tầng/không gian công cộng), **chỉ giới xây dựng** (giới hạn xây dựng công trình chính), **khoảng lùi** (giữa hai chỉ giới), **ranh thửa đất** và **trục định vị** (đường tham chiếu bố trí cấu kiện). Không suy ra chỉ giới từ mép đường hiện trạng, ranh thửa hay trục cột.
- Lấy vị trí chỉ giới và khoảng lùi từ hồ sơ quy hoạch, giấy phép hoặc tài liệu dự án được phê duyệt đang áp dụng; lấy hệ trục, gốc tọa độ, hướng bản vẽ và kích thước định vị từ tổng mặt bằng/bản vẽ trục phối hợp đã chọn làm căn cứ. Ghi tên và phiên bản tài liệu căn cứ để so giữa các bộ môn.
- Với cùng tòa nhà và cùng phiên bản thiết kế, tổng mặt bằng, kiến trúc, kết cấu và bộ môn liên quan dùng chung vị trí chỉ giới và hệ trục chính. Mặt bằng tầng có thể chỉ hiện một phần hệ trục hoặc thêm trục phụ; lưới riêng của khối nhà phải nối được với hệ tọa độ và tổng mặt bằng chung. Hình dạng công trình thay đổi theo tầng không tự làm đổi chỉ giới hoặc tọa độ trục chính.

## Mỗi lần lập mặt bằng tầng hoặc mặt bằng định vị tòa nhà

Đây là **quy ước kiểm tra của bộ hồ sơ theo yêu cầu người dùng**, không phải câu chữ bắt buộc mọi tờ bản vẽ phải thể hiện toàn bộ chỉ giới trong TCVN 5570:2012.

1. Trước khi vẽ, nạp và kiểm tra chỉ giới đường đỏ, giới hạn xây dựng áp dụng cho khối/tầng đó và hệ trục chính từ cùng phiên bản tài liệu căn cứ.
2. Trên tổng mặt bằng, thể hiện chỉ giới đường đỏ, giới hạn xây dựng của từng khối, hệ trục chính và kích thước định vị liên quan.
3. Trên mỗi mặt bằng tầng, thể hiện các trục chính dùng để định vị tầng. Thể hiện chỉ giới/giới hạn xây dựng liên quan nếu nằm trong khung hình; nếu nằm ngoài khung, đặt sơ đồ định vị **trên cùng tờ**, dẫn chiếu tổng mặt bằng và ghi kích thước từ chỉ giới đến công trình. Bản vẽ chi tiết khác chỉ cần các đường liên quan.
4. Nếu thiếu vị trí chỉ giới hoặc hệ trục làm căn cứ, áp dụng ranh giới trách nhiệm ở trên: không dựng nháp các đường định vị chưa xác minh trong CAD; chỉ dựng phần độc lập đủ căn cứ và chưa kết luận mặt bằng đã hoàn chỉnh hoặc phù hợp quy hoạch.

## Khối cao tầng và thấp tầng

- **Hai khối tách biệt:** xác định ranh vị trí, giới hạn xây dựng và khoảng lùi áp dụng cho từng khối theo quy hoạch được duyệt. Một khu đất không tự có hai chỉ giới đường đỏ chỉ vì có hai khối. Hệ trục riêng của từng khối phải có quan hệ tọa độ rõ với tổng mặt bằng.
- **Khối đế và tháp phía trên:** theo mục 2.6.2 QCVN 01:2021/BXD, xét khoảng lùi phần đế và tháp riêng theo chiều cao tương ứng, cùng với đồ án quy hoạch chi tiết/thiết kế đô thị được duyệt. Ghi rõ giới hạn nào thuộc đế, giới hạn nào thuộc tháp. Trên tầng chuyển tiếp, thể hiện quan hệ giữa hai dấu chân công trình và kích thước lùi. Không mặc định giới hạn của đế áp dụng cho tháp.

Khi rà soát, so mã trục, hướng, tọa độ hoặc khoảng cách trục, khoảng từ chỉ giới đến công trình/trục và điểm giao trục trên các bản vẽ cùng phiên bản. Nếu có sai khác, xác định bản căn cứ và lịch sử sửa đổi, rồi báo xung đột để phối hợp cập nhật; không tự dịch trục hoặc đổi chỉ giới trên riêng một tờ.

Nguồn: [QCVN 01:2021/BXD, PDF cục bộ](references/QCVN_01_2021_BXD.pdf), mục 1.4.22-1.4.24 và 2.6.2; [bản gốc trên Công báo](https://congbaocdn.chinhphu.vn/CongBaoCP/VanBan/2021/5/33751/35832-1-2021599-60001-2021-tt-bxd.pdf).
