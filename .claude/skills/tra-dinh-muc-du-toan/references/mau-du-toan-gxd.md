# File mẫu dự toán GXD (xlsm)

Mẫu: [MAU_du_toan_GXD_trong.xlsm](MAU_du_toan_GXD_trong.xlsm), cùng thư mục với trang này. Khi lập dự toán xây dựng (nhất là cải tạo, sửa chữa nhà), **bắt đầu từ bản sao của mẫu này**, không dựng bảng tính mới. Mẫu lấy từ một dự toán cải tạo nhà ở đã làm xong trên phần mềm Dự toán GXD, đã xóa toàn bộ khối lượng; còn lại khung công thức, 158 dòng công tác theo nhóm, đơn giá phân tích và hệ số theo NĐ 206/2026 + TT 36/37/38-2026.

Mẫu có dữ liệu bản quyền của phần mềm GXD (cơ sở đơn giá): dùng nội bộ, không chia sẻ ra ngoài.

## Cấu trúc

61 sheet, 7 sheet hiện, còn lại ẩn (cover, báo cáo thẩm tra, thiết bị, lắp đặt...). Có VBA (`xl/vbaProject.bin`).

| Sheet | Vai trò |
|---|---|
| `Ts` | Thông số công trình: `K3:K10` thông tin chung; `L13` loại công trình, `L15` nhà tạm, `L16` cấp công trình, `L17` số bước thiết kế, `L18` loại báo cáo, `L20` VAT; `N35:N42` hệ số VL/NC/máy, chi phí chung, TL, thuế, nhà tạm. |
| `Du toan XD` | **Bảng nhập chính.** Hàng 5 tiêu đề, hàng 7 số cột. Mỗi dòng công tác: `D` mã hiệu định mức, `E` mã hiệu đơn giá, `F` nội dung, `G` đơn vị, **`H` khối lượng**, `I` yêu cầu kỹ thuật; `P:T` đơn giá VL/VL phụ/NC/máy lấy từ `Don gia XD`; `U:Y` thành tiền. |
| `Don gia XD` | Phân tích đơn giá chi tiết của từng dòng công tác (khối `A7 = 'Du toan XD'!A8`...). Tham chiếu theo số dòng. |
| `Don gia tong hop` | Đơn giá tự lập (mã `TH…`, `TT…`) ghép từ nhiều công tác: dòng `TH` trong `Du toan XD` lấy tên, đơn vị từ đây. |
| `TH vat tu XD` | Tổng hợp vật tư (`SUMIF` từ `Don gia XD`); cột G "giá vật tư tại thời điểm lập dự toán" là chỗ điền giá hiện hành. |
| `THCP xay dung` | Tổng hợp chi phí: trực tiếp → chi phí chung → TL → VAT → nhà tạm → dự phòng → **giá dự thầu**. |
| `TH DTXD` | Bảng tổng hợp dự toán xây dựng. |

Nhóm công tác trong `Du toan XD` (dòng `E="HM"` là tiêu đề nhóm, `E="TC"` là dòng cộng nhóm; dòng 194 cộng các nhóm):
A. Chuẩn bị, tháo dỡ, phá dỡ (8) · B. Móng (27) · C. Nền (46) · D. Kết cấu thân BTCT + thép (69) · E. Xây (88) · F. Hoàn thiện ngoài nhà + cửa ngoài (95) · G. Hoàn thiện trong nhà (110) · H. Mái (130) · Điện, điện nhẹ (143). Số trong ngoặc là dòng tiêu đề nhóm; có 158 dòng công tác, trong đó 21 dòng đơn giá tự lập (`TH`/`TT`).

## Cách lập dự toán mới từ mẫu

1. Chép mẫu ra thư mục dự án, đặt tên `YYMMDD_du_toan_<tên-công-trình>.xlsm`. Không sửa trực tiếp file mẫu trong skill.
2. Hỏi người dùng điều còn thiếu ở `Ts` (loại, cấp công trình, số bước, nhà tạm, VAT) và thay `K3:K10`.
3. Nhập **khối lượng vào cột `H` của `Du toan XD`**. Dòng công tác không dùng thì để trống (thành tiền bằng 0); mẫu mặc định để trống hết. Khối lượng phải có căn cứ bóc từ bản vẽ, ghi nguồn ở cột `I`.
4. Cập nhật giá vật tư hiện hành ở `TH vat tu XD` cột G theo nguồn giá của skill này (niêm yết hoặc DMS, xem SKILL.md); ghi nguồn.
5. **Công tác chưa có trong 158 dòng: thêm bằng `scripts/them_cong_tac_gxd.py`, không cần phần mềm GXD** (xem mục dưới). Không chèn dòng bằng tay, không làm bảng riêng ngoài khung trừ khi người dùng muốn.
6. Kiểm: `THCP xay dung` có giá dự thầu hợp lý; không có ô lỗi mới (xem dưới).

## Thêm công tác mới: `scripts/them_cong_tac_gxd.py`

Đã thử trên bản sao với 3 công tác dầm sàn (bê tông xà dầm giằng sàn mái, ván khuôn xà dầm giằng, ván khuôn sàn mái): chạy đúng, không phát sinh ô lỗi mới, chi phí trực tiếp ở `THCP xay dung` khớp tính tay đến từng đồng, vật tư gộp đúng khối lượng. Chưa thử trong giao diện phần mềm GXD (mở file để dùng chức năng của GXD có thể phản ứng khác).

```
py -3 <skill>/scripts/them_cong_tac_gxd.py spec.json
```
Ví dụ spec đầy đủ: [vi-du-spec-dam-san.json](vi-du-spec-dam-san.json). Mỗi công tác khai: nhóm (`"D."`), mã định mức, nội dung, đơn vị, khối lượng, và danh sách hao phí vật liệu / nhân công / máy lấy từ PDF định mức (tra bằng `tra_dinh_muc.py`, đọc bằng ảnh trang). Script:
- chèn một dòng vào cuối nhóm trong `Du toan XD` (cập nhật dòng cộng nhóm);
- thêm các vật tư chưa có vào `TH vat tu XD` (khớp theo MSVT ở cột B; đã có thì dùng lại, không đổi giá);
- dựng khối phân tích đơn giá ở **cuối** `Don gia XD`, nối `P,R,S,T` của dòng dự toán vào khối đó;
- tự tính lại chi phí trực tiếp từ định mức x giá và so với ô công thức; đếm ô lỗi so với nền.

Việc còn lại của người lập dự toán / agent:
- **Giá vật tư mới:** `gia: null` thì dòng vật tư mới tô vàng "CHƯA CÓ GIÁ" và giá = 0, dự toán chưa dùng được cho đến khi nhập giá ở `TH vat tu XD` cột G từ nguồn giá của skill (niêm yết hoặc DMS), ghi nguồn. Không điền số đoán. Nếu `gia` điền sẵn trong spec thì phải là giá có nguồn.
- **MSVT mới là mã tự đặt** (`VX.`, `MX.`), không phải mã cơ sở dữ liệu GXD; phần mềm GXD có thể không nhận ra khi nạp lại giá.
- Mẫu gốc là mẫu **cải tạo** (mã `SB.`, vật tư chỉ gồm loại đã dùng): công trình mới (dầm sàn, kết cấu BTCT) hầu như mọi vật tư chính đều phải thêm.
- Mã dòng định mức người dùng gõ (ví dụ `AF.32316`, `AF.83311`, `AF.83111`) có thể là mã bộ cũ, **không có** trong bộ 2026. Bộ 2026 dùng mã nhóm 5 chữ số kết thúc `00` (`AF.32300`, `AF.83300`, `AF.83100`); tra bằng `tra_dinh_muc.py code <pdf> AF.323` rồi xác nhận với người dùng trước khi đổi mã.
- Hao phí phụ thuộc cột điều kiện (chiều cao ≤28/≤100/≤200 m): chọn đúng cột, ghi vào `noi_dung`.
- Chạy trên bản sao, kiểm file kết quả bằng cách đọc `THCP xay dung` rồi báo người dùng.

## Cách ghi file (quan trọng)

- **Dùng Excel qua COM, không dùng openpyxl để lưu.** openpyxl bỏ phần "Data Validation extension" và print area của sheet; mẫu mất một phần định dạng. openpyxl chỉ dùng để **đọc** (`data_only=True` xem số).
- Mở vô hiệu macro rồi lưu lại vẫn giữ VBA:
  ```powershell
  $xl = New-Object -ComObject Excel.Application
  $xl.Visible = $false; $xl.DisplayAlerts = $false; $xl.AutomationSecurity = 3
  $wb = $xl.Workbooks.Open($path, 0, $false)
  # ... sửa ô ...
  $xl.Calculate(); $wb.SaveAs($path, 52); $wb.Close($false); $xl.Quit()
  ```
  (`52` = xlsm.) Làm trên bản sao; đóng Excel xong mới báo người dùng.
- **Đừng dùng `Range.End(xlUp)` để tìm dòng cuối trên file này:** đã trả sai (chèn nhầm vào giữa khối đơn giá cuối). Quét `Range.Value2` rồi tìm dòng cuối.
- Dò ô lỗi: `$sheet.UsedRange.SpecialCells(-4123, 16)`. **Nền lỗi sẵn có của mẫu** (không phải do bạn gây ra): `Config` 18, `Don gia tong hop` 30, `TH gia du thau` 2, và 1 ô mỗi sheet `Ts`, `Bia-Dutoan`, `Bia-DTXD`, `Bia-DTTB`, `TM`, `Tai lieu`, `Dich thuat`, 2 ô mỗi sheet `BC tham dinh`, `BC tham tra`. Có thêm lỗi ngoài danh sách này thì phải xử lý. Cột tỷ trọng `TH vat tu XD` đã bọc `IFERROR` để khỏi lỗi `#DIV/0!` khi tổng bằng 0.

## Còn dấu vết công trình gốc

Một số chữ trong mẫu còn đặc thù cho công trình đã dùng làm gốc; rà lại khi sang công trình khác:
- `Don gia tong hop` ô H46: nói về "ranh lô", "gối lanh tô".
- `TH vat tu XD` ô C82: máng xối "giằng cổng, mép phía ranh thấp hơn".
- `Du toan XD` tiêu đề nhóm E (dòng 88): "gạch ống 8x8x18, VXM M75".
- Tên các dòng công tác ghi kích thước cụ thể (ví dụ "cột BTCT 200x200", "cửa xếp mặt tiền"): sửa cho khớp bản vẽ mới.
