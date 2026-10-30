---
name: autocad-trace-floor-outline
description: Dựng đường bao một tầng (viền sàn/tường ngoài) khi bản vẽ không có sẵn vòng kín, bằng cách truy biên từ các đoạn tường/kính rời trong bản sao DXF, bám trục, đo sai lệch và diện tích. Dùng khi người dùng nói 'viền sàn', 'đường bao tầng', 'tường rời chưa khép kín', 'truy biên', hoặc cần nền cho mặt bằng kết cấu; không dùng để xác định ranh khu đất.
---

# Dựng đường bao tầng từ hình học tường rời

Bổ sung cho [autocad-identify-and-measure](../autocad-identify-and-measure/references/boundaries.md) (tìm ranh đất, chọn đúng khối/tầng, xếp mức chắc chắn) và [autocad-agent-coordinator](../autocad-agent-coordinator/SKILL.md) (kết nối MCP). Dùng skill này khi đã chọn đúng tầng nhưng **không có polyline/hatch nào là viền tầng**, mà chỉ có nhiều đoạn tường, kính, cửa sổ rời nhau. Kết quả là đường bao **suy ra từ hình học**, không phải đối tượng có sẵn; luôn ghi rõ như vậy.

## Quy tắc bắt buộc

- Chỉ **đọc** bản vẽ nguồn. Không sửa, không lưu đè. Chỉ đọc đúng bản vẽ người dùng đã giao (ví dụ mặt bằng kiến trúc). Không mở hay đọc bản vẽ khác (đặc biệt bản kết cấu gốc) khi người dùng chưa cho phép.
- Trước **mọi** lệnh, kiểm tra bản vẽ đang hoạt động bằng `transaction.context` (tên file, `doc_id`, revision). Người dùng có thể chuyển tab bất cứ lúc nào; lệnh sửa trả `E_DOCUMENT_ID_MISMATCH` thì dừng, kích hoạt lại đúng bản vẽ rồi mới làm tiếp. Không đọc, không xuất kết quả của một bản vẽ chưa xác nhận.
- Thông báo cách làm trước khi sửa bản vẽ đích; báo các bước chưa kiểm được.

## Quy trình

1. **Chọn tầng và hệ tọa độ.** Nếu một DWG có nhiều mặt bằng đặt cạnh nhau (ví dụ tầng 3 và tầng 4–7), chọn một mặt bằng bằng hệ trục và tên tầng. Ghi phép dịch từ tọa độ nguồn sang tọa độ đích (`offset`), lấy từ hai trục đã biết, không ước lượng.
2. **Xuất bản sao DXF** (chỉ khi người dùng yêu cầu, hoặc đã hỏi và được đồng ý, hoặc không có kết nối AutoCAD; xem mục "Chỉ tạo file DXF" của `autocad-agent-coordinator`) của bản vẽ nguồn bằng `drawing.save_as_dxf` (kèm `doc_id`, `expected_revision`, `lease_token`) vào thư mục tạm. Xác nhận `active_document_preserved` và revision không đổi. Phân tích bằng script, không đọc từng đối tượng qua MCP. `drawing.audit` trên DWG lớn trả kết quả quá dài và bị lưu ra file; đọc file đó bằng script nếu cần.
3. **Chọn layer đưa vào truy biên.** Thống kê đối tượng theo layer trong cửa sổ của tầng. Lấy tường, kính, cửa sổ, đường viền sàn. Bỏ trục, kích thước, chữ, nội thất, hatch vật liệu, khung tên. Nếu có ranh đất trong vùng, áp dụng skill nhận diện ranh để loại ra. Ghi layer đã dùng và số đối tượng.
4. **Truy biên** bằng [scripts/trace_outline.py](scripts/trace_outline.py) trong `.venv` của MCP (có `ezdxf`, `numpy`, `matplotlib`), chạy với `python -I`:

   ```
   python -I trace_outline.py --dxf <ban_sao.dxf> --layers <layer...> \
     --offset <dx> <dy> --bbox <x0 y0 x1 y1> \
     --snap-x <toa do truc so...> --snap-y <toa do truc chu...> --out <thu_muc>
   ```

   `--bbox` (hệ đích) lấy từ hình bao sàn nếu có, nếu không thì từ phạm vi hệ trục. Chỉ đối tượng nằm **trọn** trong bbox được dùng. Script in số đối tượng theo layer, số contour, số đỉnh, diện tích đường truy được; với `--snap-*` in thêm phương án bám trục, diện tích và sai lệch lớn nhất.
5. **Xem ảnh `outline_check.png`** và đối chiếu với mặt bằng thật. Nếu có hơn một contour, kiểm tra khối rời. Nếu đường truy có răng cưa, xem tường biên có bị hở không rồi tăng `--close`.
6. **Chốt đa giác cuối.** Phương án bám trục tự động chỉ là gợi ý (thử các `--snap-eps` 600–1600). Đa giác cuối thường là các góc nằm trên trục, chọn dựa vào ảnh. Ghi những đỉnh không nằm trên trục và các ô lõm/ban công bị bỏ qua. Chấp nhận khi diện tích đa giác và diện tích đường truy lệch dưới khoảng 1% và sai lệch lớn nhất được giải thích (ô lõm nhỏ). Nếu không đạt, trả lại cho người dùng, không tự làm tròn tiếp.
7. **Vẽ vào bản vẽ đích** (đã kích hoạt và xác nhận): tạo layer (mặc định kết cấu: `A-FLOR`, ACI 192), `entity.create_polyline` kín với `layer` và `data.closed=true`. Đọc lại `area` AutoCAD báo và so với diện tích đã tính.
8. **Ghi chú trên bản vẽ** (chữ không dấu, layer `A-ANNO-NOTE`): nguồn, phương pháp "suy ra từ hình học", diện tích, điều chưa thể hiện. Không để người sau tưởng đây là đối tượng gốc.
9. **Kiểm tra hiển thị.** Cạnh nằm đúng trên trục sẽ chồng lên đường trục; ảnh `drawing.render_preview` là đơn sắc (`monochrome.ctb`), bỏ qua màu và độ dày nét nên không phân biệt được. Kiểm tra bằng ảnh vẽ từ DXF xuất lại (viền đỏ chồng lên tường nguồn). Đặt độ dày nét layer để nhìn rõ trong AutoCAD và nói rõ với người dùng.

## Kết luận

Theo thang của skill nhận diện ranh: thường là **vừa** (hình học đủ, nhưng đường bao suy ra, bám trục và bỏ ô lõm); **thấp** nếu tường biên hở nhiều hoặc chỉ dựa vào một layer. Báo: bản vẽ nguồn và tầng, layer đã dùng, số đối tượng, offset, số đỉnh, diện tích hai phương án, sai lệch lớn nhất, những gì chưa thể hiện. Tách rõ đã xác minh / suy ra / chưa kiểm được.

## Lỗi công cụ đã gặp (beiming MCP)

- `drawing.open` với đường dẫn tiếng Việt có thể báo thành công nhưng không kích hoạt bản vẽ; luôn đọc lại `transaction.context`. Nếu người dùng đã mở sẵn file, đừng mở lại; dùng `drawing.activate`.
- Sau khi người dùng đóng và mở lại, bản vẽ có `doc_id` mới (`Unknown document id`); đọc `transaction.context` để lấy `doc_id`, revision và `lease_token` mới.
- Lệnh sửa cần `doc_id`, `expected_revision`, `lease_token`; revision tăng sau mỗi lần sửa. `save`, `save_as_dxf`, `render_preview` cũng cần chúng.
- `drawing.save` lưu vào thư mục đầu ra của MCP (`...\output\drawings`), không theo đường dẫn người dùng đưa; báo đường dẫn thật.
- `entity.erase`: handle chỉ gồm chữ số cần thêm số 0 đầu (`0103`); handle có chữ cái dùng nguyên (`1AB`).
- `entity.create_batch` không hỗ trợ kích thước. Dùng `annotation.create_dimension_linear` từng cái; cỡ chữ lấy từ kiểu kích thước trong bản vẽ và không đổi được qua MCP. Muốn kích thước đẹp và đúng kiểu, chép từ bản nguồn bằng `copy_region_between_dwgs`.
- `copy_region_between_dwgs`: bản vẽ nguồn phải đang hoạt động. **Phóng to (`view.zoom_window`) vào vùng cần chọn trước khi `preview`**, nếu không vùng chọn có thể thiếu đối tượng. Chạy `preview`, kiểm tra danh sách handle (thu hẹp cửa sổ để loại đoạn lạ như đầu gấp khúc của trục), rồi `copy` với đúng `expected_handles`, `offset` và `idempotency_key` mới.
- `drawing.render_preview` có thể ra ảnh xoay 90°; xoay lại trước khi xem.
- `system.execute_lisp` bị tắt theo cấu hình (`AUTOCAD_MCP_ALLOW_ARBITRARY_LISP`). Không tự bật; hỏi người dùng nếu thật sự cần.
