---
name: autocad-redraw-from-reference
description: Quy trình đầu-cuối khi người dùng đưa bản vẽ tham chiếu (PDF và/hoặc DWG/DXF) và nói 'vẽ lại', 'dựng lại', 'vẽ theo bản này', 'chuyển PDF sang CAD'. Xác nhận mặt bằng kết cấu hay kiến trúc, rẽ sang đúng skill dựng hình; gồm đọc nguồn, tìm cụm giống nhau để chép, duyệt kế hoạch, dựng theo mốc, kiểm tra bằng số và bàn giao.
---

# Vẽ lại bản vẽ từ tài liệu tham chiếu

Dùng khi người dùng đưa PDF, DWG/DXF (hoặc cả hai) và yêu cầu vẽ lại. Skill này chỉ điều phối trình tự; phần chuyên môn nằm ở các skill được dẫn tới. Kết nối MCP, thông báo trước khi sửa và kiểm tra sau khi sửa theo [autocad-agent-coordinator](../autocad-agent-coordinator/SKILL.md). Nếu người dùng dặn chưa kết nối MCP thì chỉ làm các bước đọc file và lập kế hoạch.

## 1. Xác định loại bản vẽ, rồi xác nhận với người dùng

Làm bước này trước mọi việc khác, vì loại bản vẽ quyết định skill, thứ tự dựng và phép kiểm tra.

1. Tự nhận diện từ chứng cứ, ghi rõ căn cứ:
   - **Mã bản vẽ hoặc tên file:** `S-xxx` hay "KẾT CẤU", "FRAMING PLAN" → kết cấu; `A-xxx` hay "KIẾN TRÚC", "MẶT BẰNG TẦNG" → kiến trúc.
   - **Layer:** `S-BEAM`, `S-COLS`, `S-GRID`, bảng "SÀN DÀY …" → kết cấu. `A-FLOR-FURN`, `A-FLOR-DOOR`, `A-TAGS-ROOM`, `P-FIXT` → kiến trúc.
   - **Nội dung:** có dầm, nhãn dầm, chiều dày sàn → kết cấu; có nội thất, thiết bị vệ sinh, cửa, tên phòng, diện tích căn hộ → kiến trúc.
   - **Thư mục nguồn**, ví dụ `2. Ket cau` hay `1. Kien truc`.
2. **Luôn hỏi người dùng xác nhận**, kể cả khi chứng cứ rõ, kèm căn cứ đã thấy. Ví dụ: "Đây là mặt bằng kết cấu tầng 3 (mã S-405, có layer S-BEAM, bảng chiều dày sàn), đúng không?"
3. Xử lý các trường hợp đặc biệt:
   - **Bản lẫn cả hai** (bản kết cấu có nền kiến trúc, hoặc bản kiến trúc có cột): hỏi người dùng cần vẽ lại phần nào.
   - **Người dùng muốn chuyển loại** (từ bản kiến trúc dựng mặt bằng kết cấu): bản nguồn là kiến trúc nhưng sản phẩm là kết cấu. Đi theo nhánh kết cấu, dùng bản kiến trúc làm căn cứ.

Chỉ sang bước 2 khi loại bản vẽ đã được xác nhận.

## 2. Hỏi rõ phạm vi

Chỉ hỏi những gì ảnh hưởng tới cách làm:
- Mục đích: dựng file sạch theo chuẩn layer dự án, sao chép y nguyên, hay chuyển hệ?
- Vẽ toàn bộ hay một phần (tầng, khu, view)?
- Làm file DWG mới hay sửa trực tiếp trên file có sẵn? Tên và đường dẫn file đích?

## 3. Kiểm tra đầu vào

Theo [autocad-verify-drawing-inputs](../autocad-verify-drawing-inputs/SKILL.md):
- PDF và DWG phải cùng phiên bản (mã bản vẽ, ngày, nội dung). Lệch thì báo, không tự chọn.
- **DWG/DXF là căn cứ cho tọa độ và số đo; PDF chỉ để đối chiếu hình ảnh và ghi chú.** Chỉ đo trên PDF khi không có file CAD, và gọi kết quả đó là ước lượng.
- Xác định đơn vị (INSUNITS), tỉ lệ, các view nằm chung trong Model.

## 4. Đọc và lập danh mục bản nguồn (chỉ đọc)

- Đọc DXF hoặc đọc qua MCP. Đếm entity theo layer, tách từng view (mặt bằng, mặt cắt, bảng chú thích), ghép lại chữ tiếng Việt bị tách.
- Nhận diện đối tượng theo [autocad-identify-and-measure](../autocad-identify-and-measure/SKILL.md). Phương pháp đọc theo loại:
  - **Kết cấu:** `.llmwiki/wiki/concepts/doc-mat-bang-ket-cau-revit.md`. Đếm trục, cột, vách và cột dẹt, lỗ mở, dầm và nhãn dầm, vùng chiều dày sàn, hạ sàn.
  - **Kiến trúc:** `.llmwiki/wiki/concepts/doc-mat-bang-kien-truc-revit.md`. Đếm trục, tường, cột, cửa, phòng, căn hộ, thiết bị, nội thất, cây xanh.

## 5. Tìm cụm giống nhau

Theo [autocad-copy-similar-objects](../autocad-copy-similar-objects/SKILL.md):
- Nhóm các cụm lặp lại (phòng WC, căn hộ, cột cùng tiết diện, cụm cửa).
- Phân loại mỗi nhóm: giống hệt, giống nhưng lật hoặc xoay, hay chỉ gần giống (kèm chỗ khác).
- Mỗi nhóm chọn một mẫu: vẽ mẫu một lần, các vị trí còn lại sao chép hoặc lật từ mẫu.
- Nếu có file DWG gốc, phần không cần đổi quy ước có thể chép thẳng từ file gốc bằng `copy_region_between_dwgs` (chạy preview rồi copy), không phải vẽ tay.

## 6. Báo kế hoạch, chờ duyệt

Trình cho người dùng trước khi vẽ:
- Loại bản vẽ đã xác nhận, phạm vi, file đích.
- Danh mục đối tượng sẽ vẽ, các mẫu và vị trí sẽ sao chép hoặc lật, phần chép từ file gốc.
- Các điểm `CẦN XÁC NHẬN`.

Không vẽ gì trước khi người dùng đồng ý.

## 7. Dựng theo nhánh, duyệt theo mốc

- **Kết cấu:** dựng theo thứ tự và quy tắc của [autocad-structural-floor-plan](../autocad-structural-floor-plan/SKILL.md). Với bản vẽ khác mặt bằng (móng, mặt cắt, chi tiết), dùng [autocad-structural-drawing](../autocad-structural-drawing/SKILL.md). Các quy tắc chính:
  - Dầm chính đặt trên cột hoặc vách thật, không đặt theo trục.
  - Vẽ dầm liền qua vách mỏng hơn bề rộng dầm.
  - Hatch vùng sàn và hạ sàn làm sau dầm.
- **Kiến trúc:** theo [autocad-start-construction-drawing](../autocad-start-construction-drawing/SKILL.md). Thứ tự: trục, tường và cột, cửa, thiết bị và nội thất (sao chép hoặc lật từ mẫu), tên phòng và diện tích, kích thước, ghi chú.
- **Cả hai nhánh:** dựng lưới trục sớm và đối chiếu tọa độ với bản nguồn để phát hiện sớm lệch gốc, xoay hoặc sai tỉ lệ.
- Sau mỗi mốc (nền và trục; cấu kiện chính; chi tiết; ghi chú và kích thước), gửi ảnh cho người dùng duyệt rồi mới làm tiếp.

## 8. Kiểm tra bằng số

- Số entity theo layer: bản mới so với bản nguồn (N/N). Giải thích mọi chênh lệch.
- Tọa độ các điểm then chốt (giao trục, góc tường, tâm cột) lệch bao nhiêu mm so với bản nguồn.
- Không có đối tượng trùng hoặc chồng; không có gì chạm lỗ mở (kiểm tra cả lỗ nằm trên layer phụ). Khi dầm và lỗ va nhau, đo cả hai so với bản nguồn trước, rồi mới quyết định sửa bên nào.
- Riêng kết cấu: đường truyền tải của dầm về tới cột hoặc vách; kích thước ô sàn.
- Đặt ảnh bản mới cạnh PDF hoặc bản nguồn để người dùng so bằng mắt.

## 9. Bàn giao

- Đường dẫn file, đã lưu hay chưa.
- Phần vẽ mới, phần sao chép hoặc lật từ mẫu, phần chép từ file gốc.
- Chỗ khác bản nguồn và lý do; các mục `CẦN XÁC NHẬN`.
- Ghi kiến thức rút ra vào `.llmwiki/wiki` (trang entity của bản vẽ, cập nhật index và log).
