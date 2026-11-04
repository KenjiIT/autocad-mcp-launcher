# Bảng giá nội bộ DMS (file `gia-mat-hang-DMS-29-07-den-29-10-2026.xlsx`)

**Dữ liệu nội bộ Coteccons, không chia sẻ ra ngoài** (ghi ở sheet "Ghi chú" của file). File này **không nằm trong skill, không commit, không đưa vào bản phát hành**; script chỉ đọc file ở đường dẫn người dùng đưa. Không chép giá, tên nhà cung cấp hay tên dự án từ file vào skill, tài liệu hay tin nhắn gửi ra ngoài. Báo cáo dùng giá này ghi "nội bộ".

## Là gì

Giá hợp đồng và phụ lục hợp đồng đọc tự động từ file Excel đính kèm hồ sơ duyệt ký trên DMS (phân hệ ME35), ngày duyệt 29/07-29/10/2026. DMS không có trường đơn giá có cấu trúc, nên mỗi file có bố cục khác nhau và máy đọc có thể sai. Báo giá PDF quét và email .msg chưa được đọc. Bốn sheet: Tổng hợp mặt hàng, Chi tiết (nguồn gốc từng dòng: tên file, sheet, dòng), Hồ sơ, Ghi chú. Script dùng sheet **Chi tiết** (không dùng sheet Tổng hợp, vì nó gom cả giá lỗi và gồm cực trị).

## Dùng khi nào, ưu tiên so với giá niêm yết

- Mặc định đơn giá vật liệu lấy **giá niêm yết** (thư mục công bố giá của Sở, xem `gia-vat-lieu-tphcm.md`).
- Khi người dùng nói dự toán cho công ty, "giá riêng", "giá nội bộ", "giá Coteccons": dùng bảng này làm **nguồn chính**, vẫn ghi giá niêm yết bên cạnh để đối chiếu. Chưa rõ thì hỏi một lần.
- Một dòng dự toán chỉ dùng **một nguồn**; không lấy dòng này từ bảng nội bộ, dòng kia từ niêm yết mà không ghi.
- Mặt hàng không có hoặc quá ít mẫu: dùng niêm yết và nói rõ.
- Giá nội bộ lệch niêm yết quá 25 %: cảnh báo và tìm nguyên nhân (chiết khấu sản lượng, điều kiện giao hàng, độ sụt, VAT) trước khi dùng.

## Chọn con số nào

- Mặc định **trung vị** khi có từ 3 mẫu trở lên **và** từ 2 dự án trở lên. Dưới ngưỡng đó, báo "ít mẫu" và đưa giá gần nhất kèm nguồn thay vì coi là giá thị trường.
- **Giá gần nhất** chỉ khi người dùng muốn bám thị trường mới nhất; đây là một mẫu. Nói rõ ngày và nhà cung cấp.
- Không dùng cực trị thấp nhất/cao nhất làm đơn giá.

## Các lỗi dữ liệu đã biết (script xử lý một phần)

- **Giá dưới 1.000 đồng** (hơn 300 dòng): hệ số hoặc nhập sai; script loại. Các giá lỗi khác (ví dụ 11.985 đồng cho bê tông) vẫn lọt nếu vượt 1.000: nhìn nhóm có khoảng cao-thấp quá rộng thì mở `rows`.
- **Một mặt hàng viết nhiều kiểu** (M300, B22.5, B22.5 (M300), độ sụt, thời gian duy trì...): script gom theo tên chuẩn hóa nhưng **mỗi biến thể là một nhóm**; các nhóm có thể chênh lớn vì điều kiện khác nhau (độ sụt, duy trì, dự án, giao tại nhà máy hay công trình). Đọc cả các nhóm, chọn nhóm đúng điều kiện công trình, không gộp.
- **Đơn vị**: cái/chiếc/pcs gộp thành "cái", mét/md thành "m". Dòng cùng tên khác đơn vị (hơn 500 tên) là nhóm khác nhau; đừng so thẳng (ví dụ "ca" với "m3" của cùng một loại bơm).
- **Dòng phụ phí** (phụ phí bê tông, phụ gia, bơm) lẫn với giá vật liệu: dùng `--exclude "phu phi"`.
- **Khối lượng âm hoặc bằng 0** (giảm trừ, hạng mục chưa dùng): giá vẫn là giá hợp đồng; script đếm riêng.
- **Thiên lệch nguồn**: một vài dự án và nhà cung cấp chiếm đa số dòng, nên "nhiều dòng" chưa chắc là "nhiều mẫu độc lập"; xem số dự án và số NCC.
- **VAT**: thường trước VAT nhưng không phải file nào cũng ghi; xem "cột giá" trong kết quả và mở file gốc nếu giá dùng để thanh toán.
- **Thép xây dựng gần như không có** trong bảng; lấy từ niêm yết hoặc hợp đồng mua tập trung khác.

## Lệnh

```
py -3 <skill>/scripts/tra_gia_dms.py info   <file.xlsx>
py -3 <skill>/scripts/tra_gia_dms.py search <file.xlsx> "be tong" "m300" --unit m3 --exclude "phu phi"
py -3 <skill>/scripts/tra_gia_dms.py rows   <file.xlsx> "xi mang" "but son" --top 10
```
Cần `openpyxl`; chạy không có `-I`.
