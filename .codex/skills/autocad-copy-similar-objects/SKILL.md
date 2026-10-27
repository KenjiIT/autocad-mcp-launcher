---
name: autocad-copy-similar-objects
description: Tìm vật thể có sẵn trong DWG giống với vật thể cần tạo (phòng, căn hộ, cột, dầm, cửa, cụm chi tiết) rồi sao chép, xoay/đối xứng và đặt vào vị trí mới thay vì vẽ lại; cũng dùng để chép vùng sang bản vẽ khác (`copy_region_between_dwgs`). Dùng khi người dùng nói 'tạo … giống …', 'thêm một … như …', 'làm tương tự', 'lặp lại', 'chép sang', 'copy sang bản vẽ khác'.
---

# Sao chép vật thể giống nhau thay vì vẽ lại

Dùng khi người dùng muốn tạo một vật thể đã có mẫu trong bản vẽ ("tạo cho tôi một căn phòng giống phòng 1", "thêm cột như cột C3 ở trục 7", "lặp căn hộ này sang bên kia"), hoặc hỏi "những phòng nào giống phòng 1". Một vật thể có thể gồm nhiều entity: tường, cửa, hatch, block nội thất, chữ, kích thước. Nhận diện mẫu theo [autocad-identify-and-measure](../autocad-identify-and-measure/SKILL.md). Kết nối MCP, thông báo trước khi sửa và kiểm tra sau khi sửa theo [autocad-agent-coordinator](../autocad-agent-coordinator/SKILL.md).

Nguyên tắc: **có mẫu đúng thì sao chép mẫu**. Chỉ vẽ mới khi không có mẫu, khi đích khác mẫu tới mức phải sửa phần lớn, hoặc khi người dùng yêu cầu vẽ mới.

## 1. Xác định mẫu

1. Tìm vật thể nguồn theo mô tả của người dùng (tên phòng, mã cột, nhãn, trục, vị trí). Nếu có nhiều ứng viên, hỏi lại hoặc nêu rõ đã chọn cái nào và vì sao.
2. Lấy **đủ tập entity của mẫu**:
   - Đường bao (tường, mép sàn) và mọi thứ nằm trong ranh: cửa, cửa sổ, nội thất, thiết bị, hatch, chữ, ký hiệu.
   - Block/xref: lấy cả INSERT; ghi điểm chèn, tỉ lệ, góc quay.
   - Không lấy lưới trục, ký hiệu trục, kích thước tổng, khung tên, hay đối tượng của cấu kiện khác chỉ đi ngang qua ranh.
3. Đánh dấu riêng **phần dùng chung với vật thể bên cạnh**: tường hoặc vách chung giữa hai phòng, dầm biên chung, đường trục chung. Phần này thường không được sao chép, vì đích đã có hoặc sẽ dùng chung với vật thể khác.
4. Chọn **điểm neo** của mẫu: một điểm dễ xác định cả ở nguồn lẫn đích, như góc trong của tường, giao trục, tâm cột. Vector sao chép bằng điểm neo đích trừ điểm neo nguồn.

## 2. Kiểm tra đích có nhận được mẫu không

- **Vị trí đích**: người dùng chỉ định, hoặc suy ra (ô trống kế bên, trục tương ứng, phía đối xứng). Nếu suy ra, nói rõ.
- **Hướng**: cùng hướng, xoay 90°/180°/270°, hay đối xứng gương (căn hộ thường đối xứng theo cặp qua vách chung).
- **Kích thước khoang đích** so với mẫu, dung sai khoảng 10 mm:
  - Khớp: sao chép nguyên.
  - Lệch ít: sao chép rồi sửa riêng các cạnh lệch (di chuyển hoặc vẽ lại đoạn tường đó; MCP không có lệnh stretch). Nói rõ phần nào đã sửa.
  - Lệch nhiều, hoặc có cột, vách, lỗ mở chắn ngang: dừng lại, hỏi người dùng nên sửa mẫu hay vẽ mới.
- **Va chạm**: phần dán vào không được đè lên cột, vách, lỗ mở, cầu thang có sẵn, và không trùng tường chung đã có ở đích.

## 3. Chọn cách sao chép

| Tình huống | Cách làm (beiming MCP) |
|---|---|
| Cùng bản vẽ, một vài entity | `entity copy` theo (dx, dy) cho từng handle, hoặc `cad_batch` gồm nhiều bước `copy` (tham số đặt trong khoá `params`) |
| Cùng bản vẽ, nhiều entity hoặc nhiều vị trí | `copy_batching`: nhiều handle × nhiều offset, tối đa 100 bản sao mỗi lần gọi, tự hoàn tác nếu lỗi |
| Cần xoay | Sao chép trước, rồi `entity rotate` (tâm = điểm neo đích) trên các handle mới |
| Cần đối xứng (lật) | Dùng thẳng `entity mirror` trên handle của mẫu (trục = tim vách chung): lệnh giữ bản gốc (`_MIRROR … _N`) và tạo bản lật, không cần sao chép trước. Lật tại chỗ = `mirror` rồi `erase` bản gốc. Mỗi lần gọi chỉ một handle, và `cad_batch` không có `mirror`: mẫu nhiều đối tượng thì gọi lần lượt hoặc gom thành block. Xoay 180° không thay được đối xứng gương. Kiểm tra chữ sau khi lật (MIRRTEXT) |
| Lặp từ 3 lần trở lên, hoặc người dùng muốn sửa một chỗ là đổi tất cả | Đề xuất gom mẫu thành block (`block define`), rồi `block insert` ở từng vị trí. Hỏi người dùng trước, vì việc này thay đổi cấu trúc bản vẽ |
| Mẫu đã là một block | Chèn thêm INSERT cùng tên block với đúng tỉ lệ và góc, không nổ block |
| Cả một vùng (từ bản vẽ khác hoặc trong cùng bản vẽ) | Xem mục 3a "Sao chép theo vùng" |

### 3a. Sao chép theo vùng

Dùng khi mẫu là cả một khu (một căn hộ, một đoạn mặt bằng) và chọn bằng khung chữ nhật nhanh hơn liệt kê từng đối tượng.

- **Chọn khung:** `window` chỉ lấy đối tượng nằm trọn trong khung; `crossing` lấy cả đối tượng chạm khung. Thường dùng `window`, vì `crossing` kéo theo tường chung, dầm dài, đường trục và kích thước tổng. Thiếu gì thì bổ sung riêng.
- **Từ bản vẽ khác sang:** `copy_region_between_dwgs`.
  1. Bản nguồn phải đang hoạt động; bản đích phải mở trong cùng phiên AutoCAD. Trên AutoCAD LT đã có nhánh riêng (`region-preview-lt`, `region-copy-lt`) nhưng chưa được kiểm chứng trên bản vẽ thật; lần đầu dùng hãy thử trên bản sao.
  2. Chạy `operation=preview` với `corner1`, `corner2`, `selection_mode`. Kết quả trả về danh sách `source_handles`; kiểm tra số lượng và layer.
  3. Chạy `operation=copy` với đúng danh sách đó làm `expected_handles`, kèm `offset` (dx, dy) nếu cần dời, cùng `doc_id`, `expected_revision`, `idempotency_key` của bản nguồn. Nếu vùng đã thay đổi kể từ lúc preview, lệnh sẽ dừng; khi đó chạy preview lại.
  - Tối đa 5.000 đối tượng mỗi lần.
  - Lệnh chặn nếu hai bản khác đơn vị (INSUNITS); chỉ đặt `allow_unit_mismatch=true` khi đã hiểu rõ hậu quả.
  - `save_target=true` sẽ lưu bản đích ngay sau khi chép; mặc định là không lưu.
- **Trong cùng bản vẽ:** `copy_region_between_dwgs` từ chối khi nguồn và đích là cùng một file. Cách làm:
  1. `entity list` theo từng layer liên quan. Kết quả có `bbox` của từng đối tượng.
  2. Lọc theo khung: bbox nằm trọn trong khung (kiểu window), hoặc giao khung (kiểu crossing).
  3. Sao chép các handle đã lọc bằng `copy_batching` (số handle × số offset ≤ 100 mỗi lần, nhiều hơn thì chia nhiều lần, mỗi lần một `idempotency_key`) hoặc bằng `cad_batch` với các bước `copy`.
  4. Đếm lại số đối tượng mới bằng số đã lọc; muốn lật thì làm tiếp như mục 3.
- Sau khi chép vùng, vẫn làm bước 4 (sửa tên, số hiệu, kích thước, phần dùng chung) và bước 6 (kiểm tra).

Lưu ý công cụ:
- Trên AutoCAD LT, các lệnh nhận điểm phải chạy với OSNAP tắt. Overlay LT đã tự tắt rồi khôi phục OSMODE; nếu dùng đường khác, kiểm tra lại vị trí sau khi dán.
- Batch lớn có thể báo hết thời gian chờ dù đã chạy xong. Đếm lại trước khi chạy lại để tránh dán hai lần; dùng `idempotency_key`.
- Không nổ block hay xref của mẫu chỉ để sao chép.

## 4. Sửa những thứ không được sao chép nguyên

- **Tên và số hiệu**: "PHÒNG 1" → "PHÒNG 2", mã căn hộ, mã cột/dầm. Hỏi người dùng nếu không rõ cách đánh số.
- **Diện tích, nhãn tính từ hình học**: tính lại, hoặc đánh dấu `CẦN XÁC NHẬN`.
- **Kích thước (DIMENSION)**: chỉ giữ những kích thước nội bộ của mẫu. Kích thước nối với trục hoặc với vật thể ngoài mẫu phải ghi lại theo vị trí mới.
- **Phần dùng chung**: không dán chồng tường, vách chung lên tường đã có. Khi đối xứng hai căn hộ qua vách chung, chỉ giữ một vách.
- **Đối tượng phụ thuộc vị trí** (lỗ kỹ thuật theo MEP, ống, cột theo lưới): không tự sao chép theo; hỏi người dùng.

## 5. Tìm các vật thể giống nhau đã có

Khi người dùng hỏi "phòng nào giống phòng 1", hoặc cần chọn mẫu tốt nhất để sao chép:
1. Cùng tên block thì cùng mẫu; so thêm tỉ lệ, góc, thuộc tính.
2. Không phải block: lập "dấu vân tay" cho từng ứng viên:
   - số entity theo layer và loại;
   - kích thước bbox;
   - danh sách tọa độ tương đối so với điểm neo, đã chuẩn hóa cho các góc xoay 0/90/180/270° và cho đối xứng gương.
3. So sánh với dung sai (ví dụ 10 mm về hình học, cùng tập block nội thất). Báo kết quả theo ba mức:
   - **giống hệt**;
   - **giống, chỉ khác hướng hoặc đối xứng**;
   - **gần giống**, kèm liệt kê chỗ khác.
4. Không kết luận "giống" chỉ vì cùng diện tích hoặc cùng tên nhãn.

## 6. Kiểm tra sau khi dán

- Số entity mới bằng số entity của mẫu (nhân số bản sao), trừ phần đã chủ động bỏ.
- Bbox của nhóm mới bằng bbox mẫu dịch đúng vector (hoặc xoay/đối xứng đúng). Đo ít nhất một điểm neo.
- Không có entity trùng hay chồng với phần có sẵn ở đích (tường chung, cột, lỗ mở).
- Layer, màu ByLayer, block giữ như mẫu.
- Xuất ảnh hoặc zoom vùng đích để người dùng xem.

## 7. Báo cáo

Nêu ngắn gọn:
- Mẫu nguồn là gì, số entity, handle hoặc khu vực.
- Phép biến đổi: vector, góc xoay, trục đối xứng.
- Phần đã bỏ hoặc sửa: tường chung, nhãn, kích thước.
- Phần cần người dùng xác nhận.
- Bản vẽ đã lưu hay chưa.
