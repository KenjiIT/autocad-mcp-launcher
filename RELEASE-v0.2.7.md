AutoCAD MCP Launcher v0.2.7

# Tiếng Việt

Thêm:

- Thao tác `entity` `inventory` (chỉ đọc): kiểm kê bản vẽ để tìm vật thể lặp lại (block cùng tên, và cụm đối tượng rời cùng hình, kể cả bản quay hoặc lật). Agent kiểm kê trước khi vẽ một vật thể; nếu đã có thì chép mẫu (`sample_handles`) thay vì vẽ lại. Kết quả được lưu theo revision bản vẽ và số đối tượng từng layer, hết hạn sau 10 phút; truyền `refresh=true` sau khi sửa tay.
- Kích thước thật trên AutoCAD LT: `annotation` `create_dimension_linear`, `create_dimension_aligned`, `create_dimension_angular`, `create_dimension_radius` tạo đối tượng `DIMENSION` qua lệnh DIM của AutoLISP. Có thêm tham số tùy chọn `text` (thay chữ đo, ví dụ `250x10=2500`) và `layer`.
- Tab "Revit pyRevit (thử nghiệm)" trong launcher: chạy máy chủ Demolinator/revit-mcp-server (mã nguồn mở của bên thứ ba) qua cổng riêng, kèm kiểm tra uv, mã nguồn và pyRevit Routes. Độc lập với tab Revit hiện có.
- Block `CIVIL-CAR-PLAN-1800x4400`: xe ô tô con nhìn từ trên (mặt bằng), mũi xe hướng +y, điểm chèn giữa mép sau. Thư viện gốc nay có 106 block.
- Skill mới `thiet-ke-phong-nha`: mẹo bố trí phòng và nhà ở (tầm nhìn từ lối vào, tiền sảnh, vị trí WC khách, hành lang phòng ngủ, áp mái, ban công mái nhỏ, thông gió mái), gồm 5 phép thử, sai lầm hay gặp và checklist. Móc vào bảng chọn skill của `autocad-agent-coordinator`. Các con số trong tài liệu nguồn là số tham khảo nước ngoài; phải xác nhận theo quy chuẩn Việt Nam.

Thay đổi:

- `autocad-agent-coordinator` có Quy tắc 3 (kiểm kê trước khi vẽ một loại vật thể, nhất là bãi xe, tầng hầm, dãy ô đỗ); `autocad-copy-similar-objects` thêm mục 0 dùng kết quả kiểm kê để chép. Cần tải lại các zip này lên Claude Desktop, cùng với `autocad-block-library`, `mat-bang-tong-the` và `thiet-ke-phong-nha` (mới).
- Skill nay ghi rõ kích thước (DIM) dùng được trên LT; chỉ khi tool báo lỗi mới vẽ kích thước bằng nét.

Giới hạn đã biết:

- Kiểm kê không thấy việc chỉ di chuyển đối tượng (số lượng không đổi) trong thời hạn lưu; dùng `refresh=true`.
- Tab Revit pyRevit mới thử về mặt giao diện và kiểm tra tự động, chưa thử với Revit đang mở thật.
- `create_dimension_radius` cần có đường tròn hoặc cung đúng tâm và bán kính (sai số 0,5) trong bản vẽ.
- Kế thừa từ v0.2.6: kho `dwgshare` chưa kiểm hình từng block; gateway (cổng 8764) không tự chạy sau khi Windows khởi động lại; bộ cài Windows chưa ký.

# English

Added:

- `entity` `inventory` operation (read-only): scans the drawing for repeated objects (blocks of the same name, and loose objects of the same shape, including turned or mirrored copies). An agent runs it before drawing an object; if one already exists it copies the sample (`sample_handles`) instead of redrawing. The result is cached per drawing revision and per-layer entity count, and expires after 10 minutes; pass `refresh=true` after hand edits.
- Real dimensions on AutoCAD LT: `annotation` `create_dimension_linear`, `create_dimension_aligned`, `create_dimension_angular`, `create_dimension_radius` now create `DIMENSION` objects through the AutoLISP DIM commands. New optional parameters `text` (replaces the measured text, e.g. `250x10=2500`) and `layer`.
- "Revit pyRevit (experimental)" tab in the launcher: runs the third-party open-source Demolinator/revit-mcp-server on its own port, with checks for uv, the source and pyRevit Routes. Independent of the existing Revit tab.
- Block `CIVIL-CAR-PLAN-1800x4400`: a passenger car seen from above (plan), nose toward +y, insertion point at the middle of the rear edge. The root library now has 106 blocks.
- New skill `thiet-ke-phong-nha`: room and house layout tips (sightline from the entrance, entry hall, guest WC position, bedroom corridor, attic, dormer balcony, roof ventilation), with 5 tests, common mistakes and a checklist. Linked from the skill table of `autocad-agent-coordinator`. The figures in the source material are foreign reference numbers; confirm them against Vietnamese codes.

Changed:

- `autocad-agent-coordinator` gets Rule 3 (take an inventory before drawing a kind of object, especially car parks, basements and parking rows); `autocad-copy-similar-objects` gets a section 0 on copying from an inventory result. Re-upload these zips to Claude Desktop, together with `autocad-block-library`, `mat-bang-tong-the` and the new `thiet-ke-phong-nha`.
- The skills now state that dimensions (DIM) work on LT; draw dimensions with strokes only when the tool reports an error.

Known limitations:

- The inventory does not see a pure move (the count stays the same) while it is cached; use `refresh=true`.
- The Revit pyRevit tab has only been tried at the interface level and by automated tests, not against a running Revit.
- `create_dimension_radius` needs a circle or arc with that centre and radius (tolerance 0.5) in the drawing.
- Carried over from v0.2.6: the `dwgshare` store's blocks have not been checked by eye; the gateway (port 8764) does not start by itself after Windows restarts; the Windows installer is unsigned.
