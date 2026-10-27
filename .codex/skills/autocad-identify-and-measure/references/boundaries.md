# Nhận diện ranh đất và khối tòa nhà

Mục tiêu là đưa ra các đường bao có bằng chứng và xác định đúng phạm vi công việc. Skill hướng dẫn suy luận từ dữ liệu các tool đang cung cấp; không bổ sung tool phát hiện hình học vào MCP. Không gọi `drawing.detect_boundaries` trừ khi danh sách tool thực tế có chức năng đó.

## Bắt đầu từ đúng bản vẽ

Thông báo ngắn cách làm, ví dụ: “Tôi sẽ xác định mặt bằng đang xét, đối chiếu layer và các đường bao với tên phòng, cột và ghi chú, rồi chỉ ra ranh đất và khối nhà dự kiến. Nếu có hai đường bao dễ nhầm, tôi sẽ đánh dấu để bạn chọn.”

- Dùng công cụ chỉ đọc để lấy tên/đường dẫn DWG đang hoạt động, Model hay layout, đơn vị, hệ tọa độ và phạm vi mặt bằng. Nếu thiếu dữ liệu, ghi rõ phần chưa xác định.
- Với dự án launcher này, dùng Beiming cho bản vẽ kiến trúc/kết cấu. Nếu có `autocad-agent-coordinator`, áp dụng quy trình kết nối của skill đó. Đọc schema tool thực tế trước khi gọi; không tự đặt tên thao tác.
- Có thể bắt đầu bằng `drawing` với `operation="audit"`, `include_entities=false` nếu schema đang dùng hỗ trợ. Sau đó lấy hình học và thuộc tính chi tiết trong vùng/layer liên quan bằng các tool sẵn có. Bản tóm tắt, dữ liệu bị cắt hoặc mẫu đối tượng không đủ chứng minh không có đường bao.
- Khi nhận diện lần đầu, cần tập đối tượng đầy đủ trong phạm vi đang xét; không dùng riêng kết quả `changed_only=true`. Nếu bị giới hạn số lượng, dùng phân trang hoặc chia vùng/layer theo khả năng thật của tool và ghi rõ độ phủ.
- Nếu DWG có nhiều tầng/mặt bằng đặt cạnh nhau, dùng tên tầng, khung nhìn và cụm hình học để chọn một mặt bằng. Không gom tất cả Model thành một tòa nhà. Khi nhiều mặt bằng đều phù hợp yêu cầu, hỏi người dùng chọn trước bước phụ thuộc.

## Xác định loại đường bao cần tìm

Phân biệt ranh khu đất, đường bao tường ngoài, mép sàn, hình chiếu mái, đường bao phần đế và đường bao tháp theo từng tầng. Một công trình có thể có nhiều đường bao đúng cho những mục đích khác nhau.

Nếu người dùng chỉ yêu cầu nhận diện, trả các loại tìm thấy cùng nhãn rõ ràng. Nếu cần tính diện tích, sao chép hoặc vẽ tiếp mà loại đường bao chưa rõ và ảnh hưởng kết quả, làm rõ loại cần dùng trước thao tác đó. Ranh khu đất trong DWG không tự chứng minh ranh pháp lý, chỉ giới đường đỏ hay chỉ giới xây dựng.

## Quy trình ưu tiên: khoanh theo ranh đất rồi lọc

Áp dụng cách khoanh vùng rộng trước, nhận diện chi tiết sau theo mong muốn của người dùng.

1. **Tìm ranh khu đất trước.** Đối chiếu layer, màu, ghi chú và hình học trong mặt bằng đang xét. Nếu có nhiều ranh hợp lý, trình bày các ứng viên để người dùng chọn; chưa chọn một vòng bất kỳ làm ranh chính thức.
2. **Nếu đã xác định được ranh:** lấy toàn bộ đối tượng nằm trong ranh làm **tập ứng viên ban đầu của khối nhà**. Chưa loại đối tượng chỉ vì màu/layer không giống tường. Đây là tập đối tượng để lọc tiếp, có thể bao gồm sân, đường nội bộ, cây, chữ và kích thước. Thông báo: “Tôi sẽ lấy các đối tượng trong ranh đất này, sau đó lọc phần thuộc tòa nhà hoặc nhờ bạn xác nhận nhóm cần giữ.”
3. **Giữ riêng nhóm chạm/cắt ranh hoặc chưa xác định được vị trí.** Không âm thầm bỏ các đối tượng đó. Dùng hình học thật để xét nằm trong ranh khi tool cho phép; nếu chỉ có chọn theo hình chữ nhật/bounding box, coi kết quả là vùng chọn sơ bộ và lọc theo ranh sau. Không dùng riêng điểm chèn hoặc tâm đối tượng để khẳng định toàn bộ block/đối tượng nằm trong ranh. Đường ranh được giữ làm tham chiếu riêng.
4. **Lọc hoặc xin xác nhận:** phân nhóm ứng viên theo cụm hình học, layer, loại đối tượng và nội dung chữ. Giữ các cụm nhà riêng biệt; nêu nhóm dự kiến giữ, nhóm phụ trợ và nhóm chưa rõ. Nếu bằng chứng đủ thì tiếp tục nhận diện đường bao; nếu chưa đủ thì nhờ người dùng chọn nhóm hoặc xác nhận tập đang khoanh. “Lấy” ở bước này là thu thập dữ liệu/phạm vi ứng viên; chỉ chép, xóa hoặc sửa đối tượng khi công việc người dùng yêu cầu có thao tác đó.
5. **Nếu chưa tìm thấy ranh hoặc không có ranh:** hỏi ngắn về màu, layer, vị trí hoặc đối tượng mẫu giúp xác định khối nhà. Ví dụ: “Tôi chưa xác định được ranh đất. Khối nhà cần lấy có màu/layer nào, hoặc nằm ở vùng nào trên bản vẽ?” Tận dụng dữ liệu đã đọc để đưa lựa chọn cụ thể, không hỏi lại thông tin đã có. Nếu cần, người dùng có thể chỉ một đối tượng mẫu hoặc khoanh vùng trên ảnh. Sau khi có chỉ dẫn, lấy tập ứng viên theo chỉ dẫn đó rồi lọc/xác nhận như trên.

Phân biệt “không có ranh” với “chưa đọc được ranh” do dữ liệu bị cắt, block/xref chưa đọc hoặc hình học hở. Có thể tiếp tục kiểm tra chỉ đọc các thông tin độc lập trong khi chờ trả lời; chưa dùng vùng chưa rõ để tính diện tích chính thức hoặc thực hiện thao tác phụ thuộc.

## Thu thập và phân biệt ứng viên

Đối chiếu đồng thời các nhóm dấu hiệu dưới đây. Layer và màu là gợi ý; kiểm tra nội dung hình học thực tế trước khi kết luận.

| Dấu hiệu | Ranh khu đất | Khối tòa nhà |
|---|---|---|
| Layer và ghi chú | Tên layer liên quan ranh đất; nhãn ranh, mốc, chiều dài cạnh đất | Layer tường, cột, mặt ngoài; tên khối/tầng |
| Hình học | Một hoặc nhiều vòng biểu diễn khu đất; có thể gồm nhiều đoạn | Vòng ngoài của tường/sàn/mái theo loại đang xét; có thể lõm, có sân trong |
| Bối cảnh | Có thể bao cả nhà, sân và đường nội bộ | Thường liên quan hệ cột, phòng, cầu thang, lõi thang |
| Quan hệ | So vị trí với khối nhà trên cùng mặt bằng | Phân biệt các nhà rời, phần đế và tháp |

Chỉ kiểm tra bao chứa khi các đối tượng cùng hệ tọa độ, cùng phạm vi mặt bằng và có hình học phù hợp. Quan hệ bao chứa chỉ hỗ trợ nhận diện; đường bao lớn nhất cũng có thể là khung bản vẽ hoặc đường đường phố.

### Quy ước của bản vẽ người dùng đã mô tả

Chỉ dùng bảng này khi bản vẽ hiện tại xác nhận đang theo quy ước đó; không áp đặt cho mọi DWG.

| Layer / ACI | Ý nghĩa hỗ trợ |
|---|---|
| `A-SITE-PROP`, ACI 6 | Ứng viên ranh khu đất mạnh khi hình học và ghi chú phù hợp |
| ACI 1, đỏ | Có thể là tường/đường bao nhưng cũng có kính, thang, dốc, lan can và kích thước |
| `S-COLS`, ACI 4 | Cột kết cấu giúp nhận diện cụm nhà |
| ACI 3 | Tên phòng, diện tích, cao độ và nhãn trục; cần đọc loại đối tượng và nội dung chữ |
| ACI 8 | Có trục nhưng cũng có nội thất và thiết bị; không gom toàn bộ thành hệ trục |
| `003-wall`, ACI 10 | Layer tường có thể chỉ được khai báo, chưa có đối tượng |

Lấy màu hiệu dụng: kiểm tra màu đối tượng, TrueColor nếu có, `ByLayer`, `ByBlock` và chuỗi block chứa nó theo dữ liệu tool cung cấp. Nếu chưa giải được kế thừa màu, đánh dấu màu chưa biết. Không suy ACI chỉ từ RGB trên ảnh; ACI 1 và 10 đều có thể hiện đỏ.

### Kiểm tra hình học

- Tìm polyline kín, region, đường biên hatch hoặc chuỗi line/arc tạo vòng; hatch có thể chỉ là vật liệu, không mặc nhiên là đường bao nhà.
- Với block/xref, cần tọa độ sau biến đổi chèn, xoay, scale và hệ tọa độ về cùng không gian. Ghi đường dẫn block/xref kèm handle để phân biệt các instance. Nếu tool không đọc được nội dung hoặc xref thiếu, báo vùng chưa đọc được.
- Phân biệt hình học thật với bounding box. Bounding box dùng khoanh vùng, không dùng làm ranh chính xác hay tính diện tích nhà có góc lõm.
- Kiểm tra đoạn hở, trùng, tự cắt, vòng trong và các cụm tách rời. Không dùng convex hull để lấp sân trong hoặc nối nhiều nhà thành một khối.
- Dung sai nối điểm phải dựa trên đơn vị và độ chính xác của dữ liệu, ghi giá trị đang dùng. Không tự sửa/nối đối tượng gốc chỉ để có vòng kín. Vòng suy diễn phải ghi rõ đoạn giả định và độ hở.
- Khi tính diện tích, cần vòng hợp lệ, xử lý cung cong và lỗ, xác định đơn vị. Nếu chỉ có ảnh hoặc geometry chưa đủ, chỉ mô tả/ước lượng có nhãn; không trả diện tích như đã đo chính xác.

## Kết luận bằng bằng chứng

Dùng mức **cao / vừa / thấp**, kèm lý do; không đưa phần trăm như xác suất đã được kiểm định.

- **Cao:** loại đường bao rõ, hình học đủ và hợp lệ, ít nhất hai nhóm bằng chứng độc lập hỗ trợ, không có xung đột đáng kể. Layer và màu đặt theo layer không tính là hai nhóm độc lập.
- **Vừa:** có ứng viên hợp lý nhưng thiếu ghi chú, một phần hình học hoặc còn ứng viên cạnh tranh.
- **Thấp:** chủ yếu dựa vào màu, ảnh, mẫu dữ liệu hoặc đường bao suy diễn.

Với mỗi ứng viên, báo ngắn: mã A/B/C, loại đường bao, bản vẽ và tầng/vùng, handle kèm block/xref nếu có, layer, trạng thái kín, bằng chứng thuận/nghịch và mức chắc chắn. Chỉ ghi diện tích khi đã tính được với đơn vị rõ ràng. Phân biệt “quan sát được”, “suy luận” và “người dùng đã xác nhận”.

Nếu còn mơ hồ ảnh hưởng công việc, dùng ảnh xuất/chụp thật có sẵn để đánh dấu A/B/C trong bản xem riêng hoặc highlight tạm nếu tool hỗ trợ. Không sinh ảnh minh họa giả thành bằng chứng CAD. Nếu chưa có khả năng tạo ảnh, mô tả bằng layer, handle, vị trí và ghi chú lân cận để người dùng chọn. Không cần hỏi lại lựa chọn người dùng đã xác nhận và vẫn còn hợp lệ.

## Ghi nhớ và kiểm tra lại

Nếu môi trường cho phép lưu ghi nhớ, lưu cùng kết quả nhận diện: đường dẫn/ID bản vẽ, phiên làm việc hoặc revision nếu có, không gian, tầng/vùng, đơn vị, loại đường bao, handle và block instance, dấu nhận diện hình học có thể lấy được, bằng chứng và xác nhận của người dùng. Chỉ báo đã lưu khi có nơi lưu thật; nếu không, giữ trong ngữ cảnh cuộc trò chuyện và nói rõ giới hạn.

Trước khi tái sử dụng, kiểm tra bản vẽ hiện tại và đọc lại các đối tượng đường bao liên quan. Handle không duy nhất giữa các DWG; không tái dùng nhận diện của DWG A cho DWG B. Nếu đổi bản vẽ, handle mất, hình học/layer thay đổi hoặc không xác minh được revision, đánh dấu kết quả cần kiểm tra lại. Khi quay lại DWG cũ vẫn phải xác minh đối tượng, không chỉ dựa vào tên file.

Yêu cầu nhận diện chỉ cần đọc dữ liệu và báo cáo. Khi người dùng đã yêu cầu sửa/vẽ/chép tiếp, dùng đường bao đủ chắc chắn trong đúng phạm vi đã được giao và kiểm tra lại bản vẽ đang hoạt động ngay trước thao tác.
