# Nhận diện và đo vật thể AutoCAD

Áp dụng khi cần tìm, phân loại hoặc đo một vật thể trong DWG. Chỉ đo khi người dùng yêu cầu kích thước, khoảng cách hoặc diện tích. Một vật thể có thể gồm nhiều `LINE`, `ARC`, `POLYLINE`, `HATCH`, `INSERT` hoặc thành phần trong block/xref; số entity không phải số vật thể.

## Quy trình nhận diện

1. Xác nhận đúng DWG, tầng/khu vực, Model hay Layout và đơn vị. Handle chỉ có ý nghĩa trong DWG đang xét. Khi dùng MCP AutoCAD, theo `autocad-agent-coordinator` để chọn kết nối phù hợp; với yêu cầu nhận diện/đo, ưu tiên đọc dữ liệu và không sửa bản vẽ.
2. Định vị theo mô tả của người dùng: trục, nhãn, thứ tự, vị trí tương đối và ảnh tham chiếu. Nếu có nhiều ứng viên, dùng tọa độ và các mốc lân cận để phân biệt. Không kết luận vật thể chỉ từ màu hoặc tên layer.
3. Thu thập hình học có thể thuộc vật thể hoặc che vật thể: đường bao, hatch, nét khuất, block/xref, kích thước ghi sẵn, lưới trục và các vật thể chồng lấn. Kiểm tra các layer liên quan, không giới hạn ở layer đang được hỏi. Với block/xref, tính đến điểm chèn, tỷ lệ và góc quay.
4. Dùng ảnh hoặc viewport để hiểu cách biểu diễn và định vị vùng cần xem; dùng hình học CAD làm căn cứ đo khi có thể truy cập. Nếu kết quả truy vấn bị cắt hoặc chỉ là mẫu, lấy đủ dữ liệu trước khi kết luận.

## Thử giả thuyết che khuất trước khi gọi hình dạng là bất quy tắc

Với cột và tường thông thường, hình dạng nền thường là chữ nhật, vuông, tròn hoặc có bề dày đều. Khi phần đang thấy có đường bao méo, xiên hoặc thiếu góc, trước tiên hãy kiểm tra giả thuyết vật thể đều đang bị che, bị hatch cắt hoặc chỉ còn lộ một phần. Đây là giả thuyết khởi đầu, không phải kết luận mặc định.

- Tìm vật thể có thể che phần đó: ranh hatch/tô đặc, tường, dầm, cấu kiện khác hoặc đường cắt. Kiểm tra xem mép bất quy tắc có trùng với biên của vật thể khác hay không và các cạnh của vật thể đang xét có dừng tại biên đó không.
- Thử nối tiếp các cạnh còn thấy để xem chúng có tạo thành hình cơ bản hợp lý không. Đối chiếu phương cạnh với lưới trục, các đường song song/vuông góc, tim cấu kiện, mô-đun, kích thước ghi chú và những vật thể lặp lại ở vị trí tương tự.
- Kiểm tra trong CAD xem cạnh bị che còn tồn tại ở layer khác, trong nét khuất, block/xref, hatch boundary hoặc entity riêng không. Xem loại entity, tọa độ, điểm đầu/cuối, giao điểm và draw order nếu có thể. Đường bao hatch không nhất thiết là đường bao đầy đủ của vật thể.
- So sánh ít nhất hai cách giải thích khi có nghi vấn: vật thể có hình dạng thật sự bất quy tắc, hoặc vật thể có hình cơ bản nhưng bị che. Chỉ chọn cách giải thích được hình học, ký hiệu, lưới trục hoặc chi tiết lặp lại hỗ trợ.
- Không tự kéo dài cạnh, đối xứng phần thiếu hoặc ép hình thành chữ nhật chỉ vì cột/tường thường có dạng đó. Nếu không có cạnh đối chứng hay kích thước độc lập, giữ kết luận ở mức phần nhìn thấy.

## Đo kích thước

1. Xác định đại lượng người dùng muốn: kích thước toàn bộ, phần lộ ra, khoảng cách tim trục, kích thước thông thủy, diện tích hay cạnh theo phương xoay.
2. Xác nhận đơn vị DWG và hướng đo. Dùng cạnh thật hoặc tọa độ hình học; với vật thể xoay, đo theo trục cục bộ/cạnh thực, không dùng bbox toàn cục làm kích thước cạnh.
3. Chỉ dùng bounding box làm kích thước toàn bộ khi đường bao đầy đủ của đúng vật thể đã được xác minh. Bbox của `HATCH` hoặc một nhóm entity chỉ đo phần dữ liệu được chọn; nó có thể là vùng đang lộ ra, không phải toàn bộ cấu kiện.
4. Khi có phần khuất, tách rõ:
   - **Kích thước phần nhìn thấy:** đo trực tiếp từ vùng hatch/đường bao đang lộ.
   - **Kích thước toàn bộ:** đo từ đường bao hoàn chỉnh đã xác minh hoặc suy ra có chứng cứ độc lập.
5. Ghi rõ cạnh nào nhìn thấy, cạnh nào bị che và căn cứ khôi phục cạnh đó. Nếu kích thước toàn bộ chỉ được ước lượng từ tính đều, trục hoặc cấu kiện lặp lại, gọi đó là ước lượng và nêu độ chắc chắn; không trình bày như số đo trực tiếp.
6. Đối chiếu số đo với cạnh độc lập, kích thước ghi trên bản vẽ hoặc cấu kiện cùng loại. Nếu chúng không khớp, kiểm tra lại đúng đối tượng, mặt bằng/mặt cắt, đơn vị và phiên bản DWG; trình bày sai khác thay vì tự chọn một số.

## Tạo vật thể giống vật thể có sẵn

Khi người dùng muốn tạo thêm một vật thể giống vật thể đã có ("tạo phòng giống phòng 1"), hoặc hỏi những vật thể nào giống nhau, nhận diện mẫu theo skill này, rồi sao chép theo [autocad-copy-similar-objects](../../autocad-copy-similar-objects/SKILL.md) thay vì vẽ lại.

## Trả lời

Nêu tên/vị trí vật thể để người dùng nhận ra. Khi được yêu cầu đo, đưa số và đơn vị, đồng thời gọi rõ đó là kích thước toàn bộ hay phần nhìn thấy. Dẫn chứng ngắn gọn bằng layer, loại entity, handle và cạnh/tọa độ quyết định. Chỉ rõ mức kết luận:

- **Đã xác minh:** có đường bao đầy đủ hoặc kích thước độc lập xác nhận.
- **Suy ra có căn cứ:** một phần bị che nhưng hình học tiếp diễn, lưới trục, chi tiết lặp lại hoặc ghi chú hỗ trợ.
- **Chưa đủ căn cứ:** chỉ đo được phần nhìn thấy; chưa thể xác nhận kích thước toàn bộ.

Ảnh chụp có thể giúp nhận ra phần bị che, nhưng pixel không thay thế số đo CAD khi dữ liệu hình học sẵn có. Không tái sử dụng handle, tọa độ hoặc kích thước từ ví dụ hay bản vẽ khác.
