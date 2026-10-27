---
name: construction-drawing-tcvn5570
description: Áp dụng TCVN 5570:2012 khi lập, sửa hoặc rà soát ký hiệu đường trục và đường nét trên bản vẽ thiết kế xây dựng; kiểm tra loại nét, bề rộng nét, nhãn trục và bản in. Dùng khi người dùng nói 'nét vẽ', 'đường trục', 'TCVN 5570', 'kiểu đường', 'bề rộng nét', 'in bản vẽ'.
---

# Ký hiệu đường trục và đường nét theo TCVN 5570:2012

Dùng skill này khi sản phẩm có bản vẽ thiết kế xây dựng cần thể hiện hoặc kiểm tra đường trục, đường tim, đường bao, nét khuất, đường kích thước hay nét ngắt. Kết hợp với `construction-design-stages` để xác định bước thiết kế và với `autocad-agent-coordinator` khi thao tác AutoCAD. Skill này chỉ xử lý phạm vi ký hiệu đường trục và đường nét, không thay cho các tiêu chuẩn thiết kế kết cấu, kiến trúc hoặc hồ sơ khác.

Khi cần đối chiếu nguyên văn Bảng 1, Bảng 2 hoặc các hình, đọc [TCVN 5570:2012 đóng gói](references/TCVN_5570_2012.pdf). Khi cần kiểm tra chỉ giới, khoảng lùi hoặc sự thống nhất hệ trục giữa nhiều bản vẽ, dùng [construction-boundaries-grids](../construction-boundaries-grids/SKILL.md).

TCVN 5570:2012 thay TCVN 5570:1991. [Cơ sở dữ liệu VSQI](https://tieuchuan.vsqi.gov.vn/tieuchuan/view?sohieu=TCVN+5570%3A2012) ghi bản 2012 còn hiệu lực tại thời điểm kiểm tra ngày 14/10/2026. Nếu nhiệm vụ phụ thuộc vào tình trạng hiệu lực hiện tại, kiểm tra lại trên VSQI trước khi khẳng định. Đối chiếu yêu cầu tiêu chuẩn áp dụng của dự án; nếu có khác biệt, nêu rõ xung đột để người có thẩm quyền quyết định, không âm thầm đổi căn cứ thiết kế.

## Đường nét

Theo Bảng 1, lấy `d` làm bề rộng nét tham chiếu:

| Loại nét | Bề rộng | Thể hiện |
| --- | --- | --- |
| Liền rất đậm | `d` | Đường bao mặt cắt |
| Liền đậm | `d/2` | Đường bao trên mặt bằng, mặt đứng |
| Liền mảnh | `d/4` | Đường kích thước, đường dóng, chú dẫn, ký hiệu vật liệu |
| Dích dắc (nét ngắt) | `d/4` | Phần hình vẽ bị ngắt đoạn |
| Gạch dài - chấm mảnh | `d/4` | Đường trục, đường tim |
| Đứt mảnh | `d/4` | Đường bị khuất |

Giữ nét đều, rõ và đúng kiểu; độ dày bằng nhau không làm cho nét trục và nét khuất có cùng ý nghĩa. Giá trị `d` theo TCVN 8-20:2002 được tiêu chuẩn viện dẫn. Bề rộng trong Bảng 1 áp dụng cho hình vẽ tỷ lệ 1:50 và nhỏ hơn; với hình tỷ lệ lớn hơn 1:50, chọn bề rộng theo tỷ lệ hình vẽ. Không tự coi `d` là một số milimét cố định cho mọi bản vẽ.

## Màu nét vẽ

TCVN 5570:2012 không ấn định màu riêng cho đường trục, đường tim hay từng loại nét. Theo mục 6 của [TCVN 8-20:2002 được viện dẫn](references/TCVN_8-20_2002.pdf), nét vẽ dùng màu đen hoặc trắng tùy màu nền; có thể dùng các màu tiêu chuẩn khác nếu giải thích rõ ý nghĩa của chúng. Mục 7 yêu cầu ghi màu trong ký hiệu nét vẽ khi dùng màu. Vì vậy, chọn màu layer/CAD theo quy ước của dự án, ghi chú giải khi màu mang ý nghĩa, và kiểm tra bản xuất/in vẫn phân biệt được loại nét cùng bề rộng. Không suy ra tên “chỉ giới đường đỏ” buộc đường trên mọi bản vẽ thiết kế phải in màu đỏ.

### Khi thao tác AutoCAD

- Trước khi đặt màu, kiểm tra template, bảng layer, plot style đang dùng cho layout (`CTB` theo màu hoặc `STB` theo tên), cùng bản PDF/bản in mẫu đã được chấp nhận của dự án. Màu hiển thị trên màn hình không tự quyết định màu và bề rộng nét khi in.
- Tổ chức đối tượng theo layer có tên thể hiện chức năng; để `Color`, `Linetype` và `Lineweight` của đối tượng ở `ByLayer` theo mặc định, trừ trường hợp có chủ đích và được ghi rõ. Xác định màu layer cho dễ phân biệt khi biên tập, đồng thời đặt kiểu nét và bề rộng in đúng Bảng 1.
- Với `CTB`, màu chỉ số AutoCAD (ACI) chọn đặc tính in, gồm bề rộng nét theo cấu hình CTB của dự án; không áp một bảng màu → bề rộng cố định cho mọi hồ sơ. Với `STB`, kiểu in được gán theo tên cho layer/đối tượng và có thể độc lập với màu hiển thị. `monochrome.ctb` in các màu thành đen nhưng vẫn cần kiểm tra bề rộng và kiểu nét.
- Khi bàn giao DWG, kèm hoặc chỉ rõ CTB/STB và cấu hình in cần thiết. Kiểm tra `Plot Preview`/PDF ở tỷ lệ phát hành: trục, nét khuất, đường bao và đường kích thước vẫn phân biệt được; nếu màu mang ý nghĩa riêng trên bản vẽ màu, thêm chú giải.

## Đường trục

- Ghi số Ả Rập hoặc chữ cái in hoa trong vòng tròn đơn; không dùng chữ `I`, `O` vì dễ nhầm với số. Bề rộng nét chữ và số là `d/2`; bề rộng nét vòng tròn từ `d/4` đến `d/3`.
- Đường kính vòng tròn trên bản vẽ: **6 mm** khi tỷ lệ nhỏ hơn 1:200; **8 mm** từ 1:200 đến 1:100, gồm cả hai mốc; **10 mm** khi tỷ lệ lớn hơn 1:100.
- Với hệ trục trực giao, đánh số các trục theo chiều ngang từ trái sang phải; đánh chữ các trục theo chiều đứng từ dưới lên trên.
- Với hệ trục tròn, đánh số trục hướng tâm theo chiều kim đồng hồ, bắt đầu tại bán kính nằm ngang phía trái; đánh chữ trục đồng tâm từ tâm ra ngoài.
- Khi dùng Hình 2 và Hình 3, đọc hình học và nhãn trục cùng Bảng 2: các vòng đồng tâm mang chữ A, B từ trong ra ngoài; các trục theo bán kính mang số 1, 2. Trong bản PDF đối chiếu, chú thích tên của hai hình có vẻ đảo với nội dung minh họa; không dựa riêng vào tên hình để gán loại trục.
- Khi chữ đơn không đủ, tiếp tục bằng chữ ghép `AA`, `BB`, ... theo mục 4.5. Khi cần trục trung gian giữa các trục chính, theo mẫu Hình 1b (ví dụ `1a`); không tự đổi thứ tự trục chính đã được dùng trong hồ sơ.

## Các phụ lục tham khảo

- **Phụ lục A - hệ trục thẳng đứng:** Hình A.1-A.3 minh họa các bố cục mặt bằng khác nhau. Đọc chữ trục A, B, C... từ dưới lên và số trục 1, 2... từ trái sang phải. Xác định trục cần ghi theo bố cục và kết cấu thực tế; không suy ra rằng mọi cột hoặc mọi khoảng chia trong hình đều bắt buộc có một mã trục riêng. Các khoảng cách ghi trên hình chỉ thuộc ví dụ.
- **Phụ lục B - mặt bằng hình dạng bất kỳ:** Hình B.1 minh họa cùng một bộ phận đặt ở các hướng khác nhau trên tờ bản vẽ; Hình B.2 minh họa công trình có cả phần trực giao và phần xiên. Theo mục 4.4, lấy trục ngang và trục đứng của bản vẽ làm cơ sở, rồi chuyển hướng ký hiệu theo chiều kim đồng hồ cho phần không thuộc hệ trực giao hoặc hệ trục tròn. Tiếp tục hệ ký hiệu có thể đối chiếu được với phần chính và kiểm tra vị trí từng trục trên toàn mặt bằng. Không sao chép vị trí nhãn hoặc kích thước ví dụ nếu hình học dự án khác.
- Hai phụ lục là **tham khảo**. Dùng quy tắc trong thân tiêu chuẩn để quyết định, dùng hình phụ lục để kiểm tra cách thể hiện trường hợp tương ứng.

## Áp dụng và kiểm tra

Trước khi sửa, xác định bản vẽ, tỷ lệ, hệ trục chính, quy ước layer/kiểu nét và bộ môn liên quan. Áp dụng ký hiệu nhất quán giữa các bản vẽ cùng dự án. Sau khi tạo hoặc sửa, kiểm tra đối tượng và bản xuất/in ở tỷ lệ dự kiến: kiểu nét có nhận ra được, thứ bậc bề rộng có rõ, vòng tròn đạt kích thước trên giấy, ký hiệu trục không trùng hoặc lệch tham chiếu giữa các bộ môn. Nếu công cụ không cho kiểm tra bản in, nói rõ phần nào mới được kiểm trên mô hình và phần nào chưa xác minh.

Nguồn nội dung: [TCVN 5570:2012, PDF cục bộ](references/TCVN_5570_2012.pdf), các mục 1-4 và Phụ lục A-B; [TCVN 8-20:2002, PDF cục bộ](references/TCVN_8-20_2002.pdf), mục 6-7. [Nguồn tải TCVN 5570](https://www.mtu.edu.vn/Resources/Docs/Khoa%20-%20Bo%20mon/Khoa%20Xay%20dung/Tai%20lieu%20tham%20khao/TCVN/Ban%20ve/TCVN5570_2012.pdf); [nguồn tải TCVN 8-20](https://www.vr.org.vn/contents/Rules/Lists/Rules/Attachments/213/TCVN%208.20.2002.ISO%20128.20.1996.BAN%20VE%20KI%20THUAT.NGUYEN%20TAC%20CHUNG%20VE%20BIEU%20DIEN.PHAN%2020.QUY%20UOC%20CO%20BAN%20VE%20NET%20VE.pdf); [tình trạng TCVN 5570 trên VSQI](https://tieuchuan.vsqi.gov.vn/tieuchuan/view?sohieu=TCVN+5570%3A2012).
