AutoCAD MCP Launcher v0.2.6

# Tiếng Việt

Thêm:

- Kho block riêng: thư mục con của `blocks\` có tệp `index.json` là một "kho". `block insert` tìm tên block ở thư mục gốc rồi đến các kho. `block list` chỉ tóm tắt kho (số tệp theo loại); gọi `block list` với `data={"kho": ..., "category": ..., "min_width": ..., "max_width": ..., "min_depth": ..., "max_depth": ..., "limit": ...}` (mm) để xem một kho đã lọc. Các kho nằm ngoài git và không đóng gói kèm bản cài.
- Công cụ `lt-adapter/tools/import_block_pack.py`: tách một thư mục gói DWG thành một kho (mỗi block một tệp, kèm `index.json`). Chạy với `--rebase` để nhập cả các block có hình nằm xa điểm chèn gốc: công cụ dời điểm chèn về giữa mép dưới của hình.
- Tab Cài đặt của launcher hiện số tệp của từng kho riêng.
- Skill `autocad-apartment-floor-plan`: nghiệp vụ mặt bằng chung cư (kết cấu và giao thông chung đi trước, chia căn bám cột vách, tường dày thật, diện tích thông thủy, thoát nạn, checklist rà soát). Đã móc vào bảng chọn skill của `autocad-agent-coordinator`, `autocad-start-construction-drawing` và `autocad-redraw-from-reference`; cần tải lại các zip tương ứng lên Claude Desktop.
- Skill `autocad-block-library`: cách tra kho, lọc theo loại và kích thước, và quy tắc chụp ảnh kiểm sau khi chèn.

Thay đổi:

- Kho đầu tiên, `dwgshare`, nhập từ 9 gói nội thất của DWGshare.com (1.906 block, 122 MB trên máy bạn). Kho không có trong bản cài vì mỗi block mang ghi chú bản quyền cấm phân phối lại; bạn tự nhập trên máy mình.
- Khi kiểm tra cập nhật thất bại, launcher ghi lý do vào `launcher/logs/updater.log` thay vì im lặng.

Sửa:

- Bản cài từ v0.2.3 không thấy v0.2.4 và v0.2.5 vì hai bản đó đã đăng lên GitHub mà thiếu gói cài (zip và exe). Gói đã được bổ sung; từ nay bản mới chỉ phát hành bằng cách đẩy tag để quy trình tự dựng gói.

Giới hạn đã biết:

- Block của kho `dwgshare` chỉ có tên dạng `DWGshare.com_<số>`; chỉ biết loại gói và kích thước, chưa kiểm hình từng cái. Nhiều khối là cả cụm bố trí hoặc hình nhìn ngang. Agent phải chụp ảnh sau khi chèn để xác nhận.
- 20 khối quá nặng nên nhập không thành; gói "nội thất thương hiệu" chỉ nhập được 15 khối.
- Layer và màu nét bên trong block của kho chưa được kiểm hết; mới thấy block chèn lên layer `0`.
- Chưa thử chèn từ kho vào bản vẽ thật qua gateway MCP; mới thử trực tiếp trên backend.
- Chạy công cụ nhập làm AutoCAD LT nặng; một lần LT báo lỗi nghiêm trọng (`acadlt.err`) khi mở gói trang trí. Không dùng LT cho việc khác trong lúc nhập, và chỉ để một cửa sổ LT.
- Nếu có hai cửa sổ LT thì công cụ cần biến `AUTOCAD_MCP_ACAD_PID`.
- Kế thừa từ v0.2.5: nguyên nhân AutoCAD thỉnh thoảng bỏ sót phím kích hoạt chưa được loại bỏ; gateway (cổng 8764) không tự chạy sau khi Windows khởi động lại; tab Revit chưa thử với Revit đang mở thật; bộ cài Windows chưa ký.

# English

Added:

- Private block stores: a sub-folder of `blocks\` that holds an `index.json` is a "kho" (store). `block insert` looks for a name in the root folder, then in the stores. `block list` only summarises the stores (file counts per category); call `block list` with `data={"kho": ..., "category": ..., "min_width": ..., "max_width": ..., "min_depth": ..., "max_depth": ..., "limit": ...}` (mm) to see one store, filtered. Stores are outside git and are not packaged with the installer.
- Tool `lt-adapter/tools/import_block_pack.py`: splits a folder of DWG packs into a store (one file per block, plus `index.json`). Run it with `--rebase` to import the blocks whose geometry lies far from their own base point as well: the tool moves the base point to the middle of the bottom edge of the shape.
- The launcher's Settings tab shows the file count of each store.
- Skill `autocad-apartment-floor-plan`: apartment floor-plan practice (structure and shared circulation first, rooms follow columns and shear walls, real wall thickness, net-area measuring, escape routes, review checklist). Linked from the skill tables of `autocad-agent-coordinator`, `autocad-start-construction-drawing` and `autocad-redraw-from-reference`; re-upload those zips to Claude Desktop.
- Skill `autocad-block-library`: how to search a store, filter by category and size, and the rule to take a screenshot after inserting.

Changed:

- The first store, `dwgshare`, was imported from the 9 furniture packs of DWGshare.com (1,906 blocks, 122 MB on your machine). It is not part of the installer, because every block carries a copyright note forbidding redistribution; you import it on your own machine.
- When the update check fails, the launcher writes the reason to `launcher/logs/updater.log` instead of staying silent.

Fixed:

- Installs on v0.2.3 did not see v0.2.4 and v0.2.5, because both were published on GitHub without their packages (zip and exe). The packages were added; from now on a release is made only by pushing the tag so the workflow builds the packages.

Known limitations:

- Blocks of the `dwgshare` store are only named `DWGshare.com_<n>`; only the pack theme and the size are known, and no block's drawing has been checked by eye. Many are whole layout clusters or side views. An agent must take a screenshot after inserting to confirm.
- 20 blocks were too heavy to import; the "branded furniture" pack yielded only 15 blocks.
- The layers and colours of the strokes inside the store's blocks are not fully checked; blocks were only seen landing on layer `0`.
- Inserting from a store into a real drawing through the MCP gateway has not been tried; it was tried directly on the backend only.
- Running the import tool makes AutoCAD LT heavy; once LT reported a fatal error (`acadlt.err`) while opening the decor pack. Do not use LT for anything else while importing, and keep a single LT window open.
- With two LT windows open the tool needs the `AUTOCAD_MCP_ACAD_PID` variable.
- Carried over from v0.2.5: the cause of AutoCAD occasionally ignoring the dispatcher trigger is not removed; the gateway (port 8764) does not start by itself after Windows restarts; the Revit tab has not been tried against a running Revit; the Windows installer is unsigned.
