---
name: autocad-structural-floor-plan
description: Quy chuẩn dựng mặt bằng kết cấu dầm-sàn-cột trong AutoCAD qua MCP từ dữ liệu hình học đã có căn cứ: hợp đồng dữ liệu đầu vào (CSV), bảng layer, thứ tự dựng, ngưỡng kiểm tra số đo, các điểm chặn cần người duyệt và lỗi công cụ đã biết. Dùng khi agent lập hoặc tái dựng mặt bằng kết cấu một tầng; người dùng là người duyệt.
---

# Dựng mặt bằng kết cấu dầm-sàn-cột

Bổ sung cho [autocad-structural-drawing](../autocad-structural-drawing/SKILL.md) (quy trình chung), [autocad-agent-coordinator](../autocad-agent-coordinator/SKILL.md) (MCP) và [autocad-verify-drawing-inputs](../autocad-verify-drawing-inputs/SKILL.md). Skill này chỉ hướng dẫn **thể hiện** giải pháp kết cấu đã có người chịu trách nhiệm. Agent không tự bố trí cột, dầm, vách, không đổi tiết diện, không tính toán. Người dùng là người duyệt; không gọi kết quả là hồ sơ thi công hay đã kiểm tra chịu lực.

## 1. Chọn chế độ và ghi vào báo cáo

- **A. Dựng từ dữ liệu thiết kế:** đầu vào là bảng hình học do kỹ sư hoặc mô hình tính cung cấp.
- **B. Tái dựng từ bản đã duyệt:** đầu vào được trích từ một bản vẽ kết cấu đã phát hành. Bản dựng là bản sao có kiểm soát, không phải thiết kế độc lập; bản vẽ và báo cáo phải ghi "tái dựng từ <mã bản vẽ, revision>". Chỉ đọc bản nguồn khi người dùng cho phép rõ ràng; không sửa, không lưu đè.
- Kiến trúc đơn thuần không đủ để dựng. Nếu đầu vào chỉ có kiến trúc, hỏi bảng dữ liệu mục 2 hoặc dừng ở nền (trục, biên sàn, cột kiến trúc) và ghi `CẦN XÁC NHẬN`.

## 2. Hợp đồng dữ liệu đầu vào

Mỗi bảng ghi rõ nguồn, tầng, revision, hệ tọa độ (mm). Thiếu bảng nào thì phần phụ thuộc không được vẽ.

| Bảng | Cột bắt buộc | Ghi chú |
|---|---|---|
| grids | tên trục, hướng, tọa độ, đoạn bắt đầu/kết thúc | khớp kiến trúc hoặc có bảng quy đổi |
| columns | mã, x_min, y_min, x_max, y_max (hoặc tâm + tiết diện), tầng | tiết diện không suy từ kiến trúc |
| walls_cores | đoạn/cung hoặc đường bao, bề dày | lõi thang, thang máy, vách |
| beams | mã, đầu mút hoặc tim (x1,y1,x2,y2), bề rộng, chiều cao, nhìn thấy/khuất | dầm cong: tâm, bán kính, góc |
| slab_outline | đoạn/cung đóng kín | biên có đoạn hở phải báo, không tự đóng |
| slab_zones | biên, chiều dày, cao độ | kèm bảng chú thích hatch |
| openings | đường bao, loại | lỗ mở, giếng, hộp kỹ thuật |
| labels | mã, tiết diện, điểm chèn | điểm chèn chỉ là gợi ý bố trí chữ, không phải vị trí dầm |

Phân loại từng dòng: **đã xác nhận / suy ra có kiểm soát / chưa có căn cứ**. Bảng nhãn, số lượng đối tượng hay trục gần nhất không tạo ra hình học dầm.

## 3. Điểm chặn cần người duyệt

Hỏi người dùng và chờ trả lời trước khi vẽ phần phụ thuộc: thiếu hoặc mâu thuẫn cột/dầm/lõi/lỗ mở; hai nguồn lệch tọa độ; tiết diện chưa có; chế độ B nhưng chưa được phép đọc bản nguồn. Sau khi dựng xong, trình các mốc sau để duyệt: (1) nền + biên sàn + cột, (2) dầm, (3) nhãn + kích thước + ghi chú. Không gộp thành một lần giao cuối.

## 4. Layer (ByLayer, không ghi đè từng đối tượng)

Dùng template của dự án nếu có. Nếu không, bộ mặc định: `S-GRID` (8), `S-GRID-IDEN` (1), `S-COLS` (6), `S-COLS-HDLN` (52, Hidden), `S-BEAM` (12), `S-BEAM-HDLN` (1, Hidden), `S-BEAM-IDEN` (2), `A-FLOR` (192), `A-FLOR-HDLN` (190, Hidden), `A-FLOR-LEVL` (51), `A-ANNO-DIMS` (211), `A-ANNO-NOTE` (131); thêm `A-WALL`, `A-WALL-HDLN`, `A-FLOR-PATT` khi có tường/hatch sàn. Với bản vẽ nguồn, giữ đúng layer và quy ước nét của nguồn (nhiều bản vẽ thể hiện dầm bằng nét khuất `S-BEAM-HDLN`). Kiểm tra linetype `HIDDEN` đã nạp và đặt `LTSCALE` để nét đứt thấy được ở tầm nhìn toàn mặt bằng.

## 5. Thứ tự dựng

1. Tạo DWG mới, đặt INSUNITS=4 (mm), tạo layer, lưu ngay vào đường dẫn đích (xem mục 7).
2. Biên sàn (giữ nguyên cung) rồi cột (LWPOLYLINE đóng + hatch SOLID cùng layer).
3. Lưới trục: đường trục dừng sát vùng sàn; ký hiệu đầu trục ở cả bốn phía nếu bản nguồn có.
4. Lõi, tường, vách, lỗ mở.
5. Dầm theo bảng `beams`: dầm thẳng là LWPOLYLINE đóng đúng bề rộng; dầm cong là hai ARC đồng tâm cùng hai đoạn đầu (công cụ `create_polyline` của MCP không hỗ trợ bulge). Hai đầu dầm phải nằm trên mặt cột hoặc dầm khác.
6. Hatch vùng sàn theo chiều dày + bảng chú thích; cao độ và ký hiệu hạ sàn.
7. Nhãn dầm sau hình học (dầm đứng xoay 90°); kích thước; ghi chú chung và `CẦN XÁC NHẬN`.
8. Zoom vùng mặt bằng chính, xuất ảnh xem trước.

## 6. Ngưỡng kiểm tra (đo thật, báo bằng số)

- Số thực thể theo layer: biên sàn, cột, dầm (thẳng/cong), hatch, nhãn, DIMENSION; so với bảng đầu vào (đủ N/N).
- Số dầm có hai đầu chạm cột/dầm khác trong dung sai 1 mm; liệt kê dầm không thỏa.
- Số dầm nằm trong biên sàn. Nếu biên không khép kín, nói rõ chỉ kiểm bằng hình bao thay thế; không báo là đạt.
- Cặp dầm chồng/trùng nhau và dầm đè lên cột: phải bằng 0.
- Số nhãn gắn được vào dầm trên tổng nhãn; nhãn chỉ gán theo khoảng cách thì ghi "gán tạm". Mã dầm không được lấy từ nhãn gần nhất nếu bảng `beams` đã có mã.
- Kích thước là DIMENSION thật gắn điểm hình học; đo lại một vài giá trị. Chữ kích thước phải đọc được trong ảnh xem trước; nếu không, ghi `CẦN XÁC NHẬN`.
- Ảnh xem trước phải thấy rõ cột và dầm ở tầm nhìn toàn mặt bằng. Nếu chỉ thấy lưới và chữ thì chưa hoàn thành.
- So sánh với bản đích (chế độ B): số lượng theo layer, ảnh cạnh nhau; nêu thiếu sót cụ thể.

## 7. Lỗi công cụ đã gặp (beiming MCP)

- Mọi thao tác sửa cần `doc_id`, `expected_revision`, `lease_token` (revision tăng sau mỗi lần sửa). `drawing.*` nhận chúng trong `data`; `layer`, `entity`, `annotation` nhận ở cấp trên.
- `drawing.create` đặt tên có đóng dấu thời gian; dùng `save` với `path` đích. Không gọi `save` không đường dẫn (tạo file lạc `drawing-….dwg`).
- `create_batch` tối đa 500 đối tượng; kết quả lớn bị lưu ra file, đọc bằng script. Hatch cạnh polyline dùng `entity_id: "last"`.
- Kích thước: biến DIM chỉ nhận `DIMTXT`, `DIMASZ`, `DIMSCALE`, và đặt chúng không áp vào DIMENSION tạo qua COM (chữ vẫn 2.5 mm); không scale riêng từng dim. Cần dimstyle riêng thì nhờ người dùng chỉnh bằng `DIMSTYLE`, hoặc ghi `CẦN XÁC NHẬN`.
- Chữ có dấu tiếng Việt: dùng MTEXT với `\fArial|…;` (style Standard dùng SHX làm mất dấu). Nhãn dầm ASCII không bị ảnh hưởng.
- `render_preview` theo khổ ngang có thể ra ảnh xoay 90°; dùng `portrait` hoặc xoay ảnh. `plot_pdf` có thể đóng cửa sổ Microsoft Edge của người dùng; báo trước khi chạy.
- `entity_id` dạng `0660` khi handle chỉ có số; thử thêm số 0 nếu bị từ chối.
- Với bản sao nguồn: `save_as_dxf` giữ nguyên tài liệu đang mở; ưu tiên xuất DXF rồi đọc bằng `ezdxf` để thống kê, không đọc từng đối tượng qua MCP.

## 8. Báo cáo bàn giao

Nêu: chế độ A/B và nguồn (mã bản vẽ, revision); các số đo mục 6; danh sách `CẦN XÁC NHẬN`; phần đã dùng mặc định; điều công cụ không làm được; đường dẫn DWG, ảnh xem trước, báo cáo. Tách rõ **đã xác minh / cần xác nhận / chưa kiểm được**. Không gọi kết quả là bản phát hành.
