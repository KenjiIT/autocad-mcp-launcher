---
name: tra-dinh-muc-du-toan
description: Tra định mức dự toán xây dựng (TT 38/2026/TT-BXD) và lập dự toán chi phí trực tiếp - tìm mã hiệu công tác (bê tông, xây, trát, ốp lát, cốp pha, cốt thép, đào đất...), đọc hao phí vật liệu / nhân công / máy thi công, nhân với đơn giá nhân công và giá ca máy (ví dụ Quyết định 1491/QĐ-SXD-KT&VLXD TP.HCM 2024), kiểm khối lượng bóc từ bản vẽ. Dùng khi người dùng nói 'định mức', 'dự toán', 'đơn giá', 'hao phí', 'mã hiệu AF.', 'bóc tách khối lượng', 'giá ca máy', 'đơn giá nhân công', 'TT 38/2026', 'TT 36/2026', 'giá nội bộ', 'giá riêng của công ty', 'bảng giá DMS', 'chi phí xây dựng', hoặc đưa PDF định mức / đơn giá. Không thay thẩm tra dự toán chính thức; số tính ra là ước lượng có căn cứ.
---

# Tra định mức và lập dự toán

Skill này dẫn đường: tìm đúng công tác trong tập định mức, đọc đúng cột, nhân với đơn giá, và nói rõ chỗ nào chưa có căn cứ. Nguồn giá nội bộ (bảng DMS của công ty): [references/gia-noi-bo-dms.md](references/gia-noi-bo-dms.md); dữ liệu nội bộ, không chia sẻ ra ngoài. Quy trình, bảng mã và các điểm phải kiểm nằm ở [references/quy-trinh-du-toan.md](references/quy-trinh-du-toan.md), [references/cau-truc-tai-lieu.md](references/cau-truc-tai-lieu.md) (định mức, đơn giá nhân công, ca máy) và [references/gia-vat-lieu-tphcm.md](references/gia-vat-lieu-tphcm.md) (giá vật liệu, cạm bẫy khi tra).

## Hai tài liệu đã biết

| Tài liệu | Dùng để | Dạng file |
|---|---|---|
| CV 9947/BXD-VPB (29/6/2026), phụ lục thay thế TT 38/2026/TT-BXD (I-VIII) và Phụ lục V TT 36/2026/TT-BXD | Hao phí vật liệu, nhân công, máy trên một đơn vị công tác | PDF có chữ, 1.895 trang |
| Quyết định 1491/QĐ-SXD-KT&VLXD (31/12/2024, Sở Xây dựng TP.HCM) | Đơn giá nhân công, giá ca máy năm 2024, Vùng I và II | PDF quét, không có chữ |
| File `gia-mat-hang-DMS-*.xlsx` (giá hợp đồng nội bộ công ty, 29/07-29/10/2026) | Giá riêng của công ty; nguồn chính khi làm dự toán cho công ty | Excel, tra bằng `tra_gia_dms.py`; **bảo mật** |
| Thư mục "CONG BO GIA VLXD THANG 6-2026" (Thông báo 24594/TB-SXD-KTVLXD, 166 file) | Giá vật liệu xây dựng TP.HCM, 25 nhóm, giá chưa VAT, niêm yết của doanh nghiệp | Excel tra được bằng script; thép và nhiều công văn là PDF quét |

Tên file người dùng có thể khác; hỏi hoặc dò bằng `info`. Văn bản 2026 thay bản phát hành trước: không trộn với bản cũ.

## Cách làm

1. **Hỏi đủ đầu vào một lần** (xem `AskUserQuestion` nếu có lựa chọn rời): công tác gì, khối lượng hay bản vẽ để bóc, địa điểm (vùng I/II), thời điểm giá, định mức theo thủ công hay máy, có cần chi phí chung/thuế không. Thiếu thì nêu giả định, đừng tự điền.
2. **Tìm công tác** bằng script, không đọc cả PDF:
   ```
   py -3 -I <skill>/scripts/tra_dinh_muc.py search <pdf> "bê tông móng" "máy trộn"
   py -3 -I <skill>/scripts/tra_dinh_muc.py code   <pdf> AF.11200
   py -3 -I <skill>/scripts/tra_dinh_muc.py page   <pdf> 477 --to 478
   py -3 -I <skill>/scripts/tra_dinh_muc.py image  <pdf> 477 <thư-mục-tạm>/p477.png
   ```
   Cần PyMuPDF (`py -3 -m pip install pymupdf`).
   Giá nội bộ: `py -3 <skill>/scripts/tra_gia_dms.py search <file-DMS.xlsx> "be tong" "m300" --unit m3 --exclude "phu phi"`; mỗi biến thể tên là một nhóm riêng, đọc điều kiện từng nhóm.
   Giá vật liệu: `py -3 <skill>/scripts/tra_gia_vlxd.py search <thư-mục-giá> "xi mang" "PCB40"` (cần `openpyxl`, `xlrd`; **luôn thêm `--niem-yet`** khi lập đơn giá; thêm `--group "2. XI MĂNG"` để lọc nhóm); `rows` để đọc dòng tiêu đề của file trước khi lấy số. Hai file Excel của cùng một hãng có thể khác giá, và có cột chưa VAT, có VAT cạnh nhau. Số trang là thứ tự trong PDF, không phải số in ở chân trang (trang PDF 477 in số 333).
3. **Đọc bảng bằng ảnh, không tin văn bản trích.** Văn bản trích tách bảng thành từng ô một dòng, nên cột (ví dụ "≤250" và ">250") bị tách khỏi số. Luôn mở `image` trang đó, đối chiếu từng cột trước khi lấy số. Lấy đúng: mã hiệu, đơn vị tính, điều kiện cột (chiều rộng, chiều cao, loại đất...), thành phần công việc.
4. **Tính** theo công thức trong quy trình: mỗi dòng hao phí × đơn giá; cộng ba nhóm; nhân khối lượng. Chạy phép tính bằng mã hoặc bảng, ghi từng bước, không nhẩm.
5. **Báo cáo**: bảng mã hiệu, trang nguồn, hao phí, đơn giá dùng, thành tiền, rồi danh sách giả định và việc chưa có căn cứ.

## Điều không được làm

- Không bịa mã, hao phí, đơn giá hay tỷ lệ. Không có trong tài liệu đã nạp thì nói "chưa có trong tài liệu", và chỉ ra văn bản cần lấy (ví dụ tỷ lệ chi phí chung, thu nhập chịu thuế tính trước, thuế GTGT nằm ở TT 36/2026, chưa nạp).
- Không trộn đơn giá nhân công 2024 với định mức 2026 và giá vật liệu 2026 mà không nói; kể cả hệ số điều chỉnh.
- **Đơn giá vật liệu lấy giá niêm yết** (Bảng niêm yết giá, Mẫu 01 Phụ lục VIII, cột giá bán chưa VAT), theo yêu cầu của người dùng. Không lấy sheet hay file mẫu khác (VII.2, "file 737", "liên sở", báo giá) trừ khi người dùng bảo; nếu không có bảng niêm yết thì nói rõ và hỏi.
- **Chọn nguồn giá:** mặc định giá niêm yết. Người dùng nói dự toán cho công ty hay giá riêng/nội bộ thì dùng bảng DMS làm nguồn chính (trung vị khi từ 3 mẫu và 2 dự án; ít mẫu thì nói rõ), vẫn ghi giá niêm yết để đối chiếu, lệch trên 25 % thì cảnh báo. Một dòng dự toán chỉ một nguồn. Chưa rõ thì hỏi một lần.
- **Bảng DMS là dữ liệu nội bộ:** không chép giá, tên nhà cung cấp, tên dự án từ đó vào skill, commit, bản phát hành hay tài liệu gửi ra ngoài; báo cáo ghi "nội bộ".
- Giá vật liệu công bố là giá niêm yết, chưa trừ chiết khấu, **không dùng để thanh quyết toán**; ghi rõ khi báo cáo. Tra đúng khu vực, đúng điều kiện giao hàng, ghi hãng và nguồn.
- Định mức ghi "nhóm 2" (nhân công) không kèm bậc thợ: bậc thợ phải lấy theo hướng dẫn của thông tư hoặc hỏi người dùng, không tự chọn.
- Bản quét (QĐ 1491) không tra bằng script: đọc ảnh trang, ghi lại số nhìn thấy, báo đã đọc từ ảnh.
- Không ghi kết quả này là dự toán đã thẩm tra hoặc làm căn cứ pháp lý.
