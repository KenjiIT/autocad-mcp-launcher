---
name: thiet-ke-phong-nha
description: Mẹo và nguyên tắc bố trí phòng, nhà ở (nhà phố, nhà vườn, căn hộ nhỏ) - tầm nhìn từ lối vào, tiền sảnh, vị trí WC khách (gầm cầu thang, tiền sảnh, hành lang), hành lang phòng ngủ và riêng tư, tủ đồ/giặt, áp mái, ban công mái nhỏ (dormer), thông gió mái. Dùng khi người dùng nói 'bố trí phòng', 'thiết kế nhà', 'WC khách', 'tiền sảnh', 'hành lang', 'phòng ngủ', 'gầm cầu thang', 'áp mái', 'tầm nhìn', 'riêng tư', 'tối ưu diện tích nhà nhỏ', hoặc đánh giá phương án mặt bằng nhà ở. Dùng cùng autocad-start-construction-drawing khi phải vẽ; chung cư dùng thêm autocad-apartment-floor-plan.
---

# Thiết kế phòng và nhà ở: mẹo bố trí

Skill này là **bộ lăng kính đánh giá và đề xuất bố trí** (công năng, tầm nhìn, riêng tư, diện tích). Nó không thay quy chuẩn. Mọi con số (chiều cao thông thủy, diện tích tối thiểu, lan can, độ dốc mái) phải lấy từ quy chuẩn hoặc hồ sơ dự án hiện hành. Các số trong [references/meo-bo-tri.md](references/meo-bo-tri.md) chỉ là số tham khảo từ tài liệu nguồn nước ngoài, chưa chắc khớp quy chuẩn Việt Nam; phải xác nhận trước khi ghi lên bản vẽ.

Đơn vị, layer, chữ, kích thước, Layout theo [autocad-start-construction-drawing](../autocad-start-construction-drawing/SKILL.md). Nội thất và thiết bị vệ sinh tra [autocad-block-library](../autocad-block-library/SKILL.md) trước khi vẽ tay. Chung cư: kết cấu và giao thông chung đi trước, xem [autocad-apartment-floor-plan](../autocad-apartment-floor-plan/SKILL.md).

## Cách dùng

1. **Đứng ở lối vào, vẽ các trục tầm nhìn** (đường nhìn từ cửa chính đi vào). Mỗi trục nhìn thấy gì thì ghi lại.
2. **Chạy 5 phép thử** bên dưới lên phương án (của người dùng hoặc của mình). Phép thử nào trượt thì nêu lỗi, đề xuất sửa, nói rõ đổi diện tích thế nào.
3. **Báo cáo ngắn:** phép thử nào đạt/trượt, lý do, phương án sửa. Có hai cách sửa khác nhau thật sự thì hỏi người dùng bằng `AskUserQuestion`.
4. Khi sửa trong DWG: làm trên layer hoặc bản sao phương án riêng, không đè bản gốc, không lưu khi chưa hỏi.

## 5 phép thử

### 1. Tầm nhìn từ lối vào (tiền sảnh)
- Từ cửa chính **không nhìn thẳng** vào bồn cầu, giường, bếp hoặc tủ để đồ lộn xộn.
- Cửa WC khách và cửa tủ đồ **không mở thẳng ra tiền sảnh**. Nếu buộc phải, xoay hướng cho cửa mở vào hốc hoặc hành lang nhỏ, không đối diện lối vào.
- Tiền sảnh chỉ là khoảng đệm: không để nó phình to vì nhiều cánh cửa mở ra từ nhiều phía. Xoay hướng WC/tủ để thu gọn đệm, rồi đặt điểm nhấn thị giác (hốc tường trang trí, tranh, ghế băng + kệ) ở cuối trục nhìn.

### 2. Vị trí WC khách
- Đặt ở vị trí trung tâm, gần khu sinh hoạt chung để cả gia đình lẫn khách dùng thuận tiện. Mỗi lần một người dùng nên không cần rộng; khoảng thông thủy trước thiết bị có thể ở mức tối thiểu theo quy chuẩn.
- Ba kiểu phổ biến:
  - **Gầm cầu thang:** tối ưu diện tích; kiểm chiều cao đầu người trước bồn cầu theo quy chuẩn.
  - **Cạnh tiền sảnh:** tiện, nhưng cửa không mở thẳng vào tiền sảnh.
  - **Cuối hành lang phòng ngủ:** cần một hành lang đệm nhỏ để tách khu riêng tư khỏi luồng khách; đặt thẳng trong khu ngủ thì mất riêng tư.

### 3. Phòng ngủ: hành lang và tầm nhìn trực diện
- Cửa phòng ngủ **không nhìn thấy trực diện** từ khu sinh hoạt chung (bếp, ăn, khách).
- Hành lang vừa đủ: **hẹp và dài** thay vì ngắn và rộng. Hành lang rộng cỡ phòng tắm là lãng phí trong nhà nhỏ.
- Hành lang thẳng còn chứa được tủ giặt/máy giặt sấy dọc tường, WC chung, và dồn các cửa phòng ngủ về một phía.
- So hai phương án bằng diện tích hành lang trên tổng diện tích sàn; chọn phương án ít lãng phí mà vẫn che được tầm nhìn.

### 4. Áp mái và ban công mái nhỏ (dormer)
- Cửa sổ mái nhô (dormer) cho ít diện tích sử dụng thêm nhưng lấy nhiều ánh sáng và gió nếu lắp cửa đi kiểu Pháp (mở cánh kính) hoặc cửa lùa ra ban công nhỏ có lan can.
- Vùng dưới mái thấp hơn chiều cao tối thiểu quy định thì **không tính vào diện tích ở/sinh hoạt**. Chiều cao tối thiểu và chiều cao lan can theo quy chuẩn (tài liệu nguồn nêu 1,52 m và 107 cm; chưa phải số Việt Nam).

### 5. Thông gió không gian áp mái
- Áp mái không thông gió, cộng hơi ẩm từ nhà tắm, bếp, máy giặt bốc lên, gây **ngưng tụ hơi ẩm** → nấm mốc, mục gỗ, giảm hiệu quả cách nhiệt, hỏng kết cấu.
- Cần có: **lớp cách nhiệt** ở trần dưới áp mái, **cửa thông gió diềm mái** (gió vào), **cửa thông gió đỉnh/nóc mái** (gió ra), và **ống thoát hơi từ bếp, WC, máy giặt dẫn hết ra ngoài**, không xả vào áp mái.

## Sai lầm hay gặp

- Cửa WC/tủ mở thẳng ra lối vào, lộ bồn cầu từ cửa chính.
- Hành lang phòng ngủ ngắn mà rộng: tốn diện tích nhưng vẫn lộ giường.
- WC khách đặt ngay trong khu ngủ, không có đệm.
- Bồn cầu gầm cầu thang nhưng không kiểm chiều cao đầu người.
- Tính diện tích ở cả vùng áp mái quá thấp.
- Ống thoát hơi xả vào áp mái thay vì ra ngoài.

Chi tiết từng tình huống: [references/meo-bo-tri.md](references/meo-bo-tri.md). Danh mục rà soát nhanh: [references/checklist.md](references/checklist.md).
