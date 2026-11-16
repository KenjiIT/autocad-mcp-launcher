AutoCAD MCP Launcher v0.4.3

# Tiếng Việt

Bản này gỡ phần Revit thử nghiệm khỏi launcher và bổ sung nghiệp vụ cho các skill thiết kế chung cư, bóc khối lượng và dự toán.

Thêm:

- **Skill `autocad-apartment-floor-plan`:** quy trình dừng ở 5 cổng (Chỉ tiêu, Hình khối, Lõi và hành lang, Căn điển hình, Giao) để người dùng chọn phương án. Thêm 3 tài liệu tham chiếu (cổng duyệt phương án, hiệu quả diện tích, QCVN 06 cho chung cư) và các mục kiểm tra tương ứng trong checklist.
- **Skill `autocad-agent-coordinator`:** mục "Bản vẽ lớn và bóc khối lượng: đọc ngoại tuyến". Từ khoảng 100 đối tượng trở lên, đổi một bản sao DWG sang DXF bằng `scripts/dwg_to_dxf.py` (LibreDWG, cần `pip install ezdxf`) rồi đọc bằng ezdxf thay vì đọc qua MCP. Vẫn hỏi người dùng trước khi tạo DXF.
- **Skill `tra-dinh-muc-du-toan`:** hướng dẫn lập dự toán Excel từ mẫu GXD, kèm `mau-du-toan-gxd.md` (cấu trúc mẫu), `them_cong_tac_gxd.py` (thêm công tác vào mẫu bằng Excel COM) và `vi-du-spec-dam-san.json`. **Tệp mẫu `MAU_du_toan_GXD_trong.xlsm` không kèm theo** vì có dữ liệu bản quyền của phần mềm GXD; mỗi người dùng tự có bản của mình.
- **Skill `thiet-ke-phong-nha`:** ghi chú rằng chung cư phải theo QCVN 04:2021/BXD, số khác với TCVN 4451.
- Tài liệu nguồn gốc và thay đổi so với upstream Beiming: `autocad-beiming-mcp-custom/LOCAL_CHANGES.md`.

Sửa:

- **`du-toan-mcp`:** với tệp dữ liệu dự toán tải về chỉ có phần tham chiếu, công cụ tự tạo các bảng còn thiếu (dự án, người dùng...) khi khởi động.

Thay đổi:

- **Gỡ hai tab "Revit (thử nghiệm)" và "Revit pyRevit (thử nghiệm)" khỏi launcher**, cùng mã tương ứng (`revit_mcp.py`, `revit_pyrevit_mcp.py`). Ai đang dùng các tab này cần chạy máy chủ Revit MCP bằng cách khác, ngoài launcher.

Cần làm:

- Tải lại 4 zip skill lên Claude Desktop (Cài đặt, mục Skills): `autocad-agent-coordinator`, `autocad-apartment-floor-plan`, `thiet-ke-phong-nha`, `tra-dinh-muc-du-toan`.
- Thoát hẳn launcher rồi mở lại sau khi cập nhật.

Giới hạn:

- Đã chạy bộ kiểm thử: 187 đạt. Một kiểm thử (`test_second_process_is_refused_until_first_exits`, khóa một phiên bản) lỗi vì launcher thật đang chạy cùng thư mục lúc kiểm; kiểm thử này đạt khi chạy ở thư mục khác và đạt ở v0.4.2.
- Chưa mở cửa sổ launcher sau khi gỡ hai tab Revit và chưa cài thử bộ cài `.exe`.
- Chưa có kiểm thử riêng cho phần tự tạo bảng của `du-toan-mcp`.
- Các thay đổi skill là hướng dẫn quy trình, không có kiểm thử tự động.
- Các giới hạn khác giữ như v0.4.2.

# English

This release removes the experimental Revit tabs from the launcher and adds domain guidance to the apartment-design, quantity take-off and cost-estimating skills.

Added:

- **Skill `autocad-apartment-floor-plan`:** the workflow now stops at 5 gates (Targets, Massing, Core and corridor, Typical unit, Handover) so the user picks each option. Adds 3 reference documents (option review gates, area efficiency, QCVN 06 for apartment buildings) and matching checklist items.
- **Skill `autocad-agent-coordinator`:** new section "Large drawings and quantity take-off: read offline". From about 100 objects up, convert a copy of the DWG to DXF with `scripts/dwg_to_dxf.py` (LibreDWG, needs `pip install ezdxf`) and read it with ezdxf instead of reading through MCP. The user is still asked before a DXF is created.
- **Skill `tra-dinh-muc-du-toan`:** guidance for building an Excel estimate from the GXD template, with `mau-du-toan-gxd.md` (template structure), `them_cong_tac_gxd.py` (adds work items to the template through Excel COM) and `vi-du-spec-dam-san.json`. **The template file `MAU_du_toan_GXD_trong.xlsm` is not included** because it contains copyrighted data from the GXD software; each user supplies their own copy.
- **Skill `thiet-ke-phong-nha`:** a note that apartment buildings must follow QCVN 04:2021/BXD, whose numbers differ from TCVN 4451.
- Provenance and changes relative to upstream Beiming: `autocad-beiming-mcp-custom/LOCAL_CHANGES.md`.

Fixed:

- **`du-toan-mcp`:** for a downloaded estimating data file that holds only the reference tables, the tool now creates the missing tables (projects, users...) at startup.

Changed:

- **The "Revit (thử nghiệm)" and "Revit pyRevit (thử nghiệm)" tabs are removed from the launcher**, together with their code (`revit_mcp.py`, `revit_pyrevit_mcp.py`). Anyone using those tabs must run the Revit MCP server another way, outside the launcher.

To do:

- Re-upload the 4 skill zips to Claude Desktop (Settings, Skills): `autocad-agent-coordinator`, `autocad-apartment-floor-plan`, `thiet-ke-phong-nha`, `tra-dinh-muc-du-toan`.
- Quit the launcher completely and reopen it after updating.

Known limitations:

- The test suite was run: 187 passed. One test (`test_second_process_is_refused_until_first_exits`, single-instance lock) failed because the real launcher was running from the same folder during the check; the test passes from another folder and passed on v0.4.2.
- The launcher window was not opened after the Revit tabs were removed, and the `.exe` installer was not installed for this release.
- There is no dedicated test yet for the table creation in `du-toan-mcp`.
- The skill changes are workflow guidance and have no automated tests.
- Other limitations are unchanged from v0.4.2.
