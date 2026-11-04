AutoCAD MCP Launcher v0.2.9

# Tiếng Việt

Thay đổi chỉ nằm ở skill; không đổi mã launcher, gateway hay adapter.

Thêm:

- Skill mới `tra-dinh-muc-du-toan`: tra định mức dự toán xây dựng và lập chi phí trực tiếp.
  - Tra định mức trong phụ lục thay thế của TT 38/2026/TT-BXD (CV 9947/BXD-VPB): tìm theo từ khóa hoặc mã hiệu (ví dụ AF.11200), đọc hao phí vật liệu, nhân công, máy thi công, đối chiếu cột điều kiện bằng ảnh trang. Script `tra_dinh_muc.py`.
  - Đơn giá nhân công và giá ca máy TP.HCM năm 2024 (QĐ 1491/QĐ-SXD-KT&VLXD), bảng nhân công đã nạp từ ảnh.
  - Giá vật liệu TP.HCM tháng 6/2026 (Thông báo 24594/TB-SXD-KTVLXD): script `tra_gia_vlxd.py`, mặc định lấy giá niêm yết (`--niem-yet`), kèm các lỗi dễ gặp (cùng file hai sheet hai giá, cột chưa VAT và có VAT, nhiều khu vực).
  - Giá nội bộ của công ty từ bảng DMS: script `tra_gia_dms.py` gom biến thể tên, loại giá bất thường, báo trung vị khi từ 3 mẫu và 2 dự án, gắn nhãn "ít mẫu" khi dưới ngưỡng. Dữ liệu nội bộ không nằm trong skill; script chỉ đọc file ở đường dẫn người dùng đưa.
  - Quy tắc chọn nguồn giá: mặc định giá niêm yết; dự toán cho công ty thì giá nội bộ là nguồn chính, ghi giá niêm yết đối chiếu, lệch trên 25 % thì cảnh báo; một dòng dự toán chỉ một nguồn.
- Skill `autocad-agent-coordinator` có thêm một dòng định tuyến sang `tra-dinh-muc-du-toan`.

Cần làm: tải lên Claude Desktop (Cài đặt, mục Skills) `tra-dinh-muc-du-toan.zip` (mới) và tải lại `autocad-agent-coordinator.zip`. Cần cài `pymupdf`, `openpyxl`, `xlrd` (`py -3 -m pip install pymupdf openpyxl xlrd`). Giữ các file giá trên máy: skill đọc từ đường dẫn bạn đưa.

Giới hạn đã biết:

- Chưa lập thử một dự toán hoàn chỉnh bằng skill.
- QĐ 1491 là bản quét: chỉ đọc được từ ảnh; bảng nhân công đã nạp, giá ca máy từng máy chưa tra. Chưa ghép được "nhóm 2" của định mức 2026 với nhóm và bậc thợ của bảng 2024; skill bắt hỏi người dùng.
- Văn bản trích từ PDF định mức tách bảng thành từng ô, nên phải đối chiếu cột bằng ảnh trước khi lấy số.
- Giá thép (Thép Miền Nam, Vina Kyoei) đọc từ ảnh bản quét; Vina Kyoei mới đọc một trong sáu trang. Ba file .doc công văn chưa đọc được.
- Tiền tố mã AA-AN suy ra từ thứ tự chương, mới kiểm sáu tiền tố. Ngưỡng 3 mẫu, 2 dự án và 25 % do skill tự đặt.
- Giá công bố không dùng để thanh quyết toán; chi phí chung, thuế, dự phòng (TT 36/2026) chưa nạp.
- Kế thừa từ v0.2.8: skill `thiet-ke-phong-nha` chưa chạy trên mặt bằng thật trong DWG; tab Revit pyRevit chưa thử với Revit đang mở; gateway (cổng 8764) không tự chạy sau khi Windows khởi động lại; bộ cài Windows chưa ký.

# English

The change is in skills only; no change to the launcher, gateway or adapter code.

Added:

- New skill `tra-dinh-muc-du-toan`: look up construction estimating norms and build direct-cost estimates.
  - Norm lookup in the replacement appendices of Circular 38/2026/TT-BXD (Official Letter 9947/BXD-VPB): search by keyword or code (for example AF.11200), read material, labour and machine consumption, check the condition columns against a page image. Script `tra_dinh_muc.py`.
  - Ho Chi Minh City 2024 labour rates and machine-shift prices (Decision 1491/QD-SXD-KT&VLXD); the labour table was entered from page images.
  - Ho Chi Minh City June 2026 material prices (Notice 24594/TB-SXD-KTVLXD): script `tra_gia_vlxd.py`, listed (posted) prices by default (`--niem-yet`), with common pitfalls (two sheets with two prices in one file, ex-VAT and with-VAT columns, several regions).
  - The company's internal prices from the DMS table: script `tra_gia_dms.py` groups name variants, drops outlier prices, reports the median from 3 samples and 2 projects, and flags "few samples" below that. The internal data is not in the skill; the script only reads the file at the path the user gives.
  - Price-source rule: listed prices by default; for company estimates the internal price is the main source with the listed price shown for comparison and a warning above 25 % difference; one source per estimate line.
- The `autocad-agent-coordinator` skill gains a routing row to `tra-dinh-muc-du-toan`.

To do: upload `tra-dinh-muc-du-toan.zip` (new) and re-upload `autocad-agent-coordinator.zip` to Claude Desktop (Settings, Skills). Install `pymupdf`, `openpyxl`, `xlrd` (`py -3 -m pip install pymupdf openpyxl xlrd`). Keep the price files on the machine: the skill reads from the path you give.

Known limitations:

- The skill has not been used to build a complete estimate yet.
- Decision 1491 is a scan: readable only from images; the labour table is entered, individual machine-shift prices are not looked up. "Group 2" labour in the 2026 norms is not yet mapped to the group and grade of the 2024 table; the skill makes the user decide.
- Text extracted from the norm PDF splits tables into single cells, so columns must be checked against the page image before taking a figure.
- Steel prices (Mien Nam Steel, Vina Kyoei) were read from scanned images; only one of six Vina Kyoei pages was read. Three .doc cover letters could not be read.
- Code prefixes AA-AN were inferred from chapter order and only six were checked. The thresholds of 3 samples, 2 projects and 25 % are set by the skill itself.
- Published prices are not for final settlement; overheads, tax and contingency (Circular 36/2026) are not loaded.
- Carried over from v0.2.8: the `thiet-ke-phong-nha` skill has not been run on a real floor plan in a DWG; the Revit pyRevit tab has not been tried against a running Revit; the gateway (port 8764) does not start by itself after Windows restarts; the Windows installer is unsigned.
