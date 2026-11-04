AutoCAD MCP Launcher v0.2.8

# Tiếng Việt

Thay đổi chỉ nằm ở một skill; không đổi mã launcher, gateway hay adapter.

Thêm:

- Skill `thiet-ke-phong-nha` có số liệu từ bộ tiêu chuẩn nhà ở Việt Nam, tách theo loại nhà:
  - `references/tieu-chuan-nha-o.md`: TCVN 13967:2024 (nhà ở riêng lẻ), TCVN 9411:2012 (nhà liên kế, nhà phố), TCVN 4451:2012 (chung cư). Gồm diện tích phòng tối thiểu, chiều cao thông thủy, cầu thang, khoảng lùi, chiều cao nhà, ban công vươn ra, an toàn cháy nhà ở kết hợp kinh doanh, cách tính diện tích. Có bảng so sánh số khác nhau giữa nhà riêng lẻ và chung cư.
  - `references/tieu-chuan-khi-hau-nang-luong.md`: TCVN 9258:2012 (chống nóng), TCVN 14214:2024 (vi khí hậu), TCVN 13521:2022 (chất lượng không khí trong nhà), TCVN 5687:2024 (thông gió), QCVN 04-3:2026/BXD (năng lượng, công trình từ 2.500 m² sàn), QCVN 10:2024/BXD (tiếp cận, chung cư và công trình công cộng), TCVN 4605:1988 (chỉ để tính nhiệt).
- Phép thử thứ 6 của skill: hướng nhà và thông gió xuyên phòng (tránh nắng Đông - Tây, cửa đón gió và cửa thoát gió, bậu cửa sổ, giếng trời cho nhà sâu).
- Checklist thêm hai mục: hướng, nắng, gió; và tiếp cận.
- Từ khóa gọi skill mở rộng: TCVN 13967, 9411, 4451, 9258, QCVN 10, QCVN 04-3, hướng nhà, chống nóng, vi khí hậu.

Cần làm: tải lại `thiet-ke-phong-nha.zip` lên Claude Desktop (Cài đặt, mục Skills).

Giới hạn đã biết:

- Số liệu đọc từ bản Word của tiêu chuẩn; hình vẽ không đọc được, các điều "xem Hình ..." cần mở bản gốc.
- Một số chỗ cần đối chiếu bản gốc: dòng "diện tích cửa sổ không nhỏ hơn 60 %" của TCVN 9258 (8.6.4) không rõ đối tượng; bảng độ ẩm của TCVN 14214; số "0,09 m" thang lên áp mái của TCVN 4451 (có lẽ là 0,90 m); bảng vạt góc nhà góc phố của TCVN 9411.
- Là tiêu chuẩn tham khảo. Quy hoạch chi tiết, quy chế quản lý kiến trúc địa phương, QCVN 06 (an toàn cháy) và hồ sơ dự án chặt hơn thì theo đó.
- Skill chưa được chạy trên một mặt bằng thật trong DWG.
- Kế thừa từ v0.2.7: tab Revit pyRevit chưa thử với Revit đang mở; kiểm kê (`entity inventory`) không thấy việc chỉ di chuyển đối tượng trong thời hạn lưu; gateway (cổng 8764) không tự chạy sau khi Windows khởi động lại; bộ cài Windows chưa ký.

# English

The change is in one skill only; no change to the launcher, gateway or adapter code.

Added:

- The skill `thiet-ke-phong-nha` now carries figures from the Vietnamese housing standards, split by building type:
  - `references/tieu-chuan-nha-o.md`: TCVN 13967:2024 (single dwellings), TCVN 9411:2012 (row houses, town houses), TCVN 4451:2012 (apartment buildings). Covers minimum room areas, clear heights, stairs, setbacks, building height, balcony projection, fire safety of mixed residential and business use, and how areas are counted. Includes a table of the figures that differ between single dwellings and apartments.
  - `references/tieu-chuan-khi-hau-nang-luong.md`: TCVN 9258:2012 (heat protection), TCVN 14214:2024 (microclimate), TCVN 13521:2022 (indoor air quality), TCVN 5687:2024 (ventilation), QCVN 04-3:2026/BXD (energy, buildings of 2,500 m² floor area and over), QCVN 10:2024/BXD (accessibility, apartments and public buildings), TCVN 4605:1988 (heat calculation only).
- A 6th test in the skill: building orientation and cross-ventilation (avoid east-west sun, inlet and outlet openings, window sill height, light wells for deep houses).
- Two new checklist groups: orientation, sun and wind; and accessibility.
- More trigger words for the skill: TCVN 13967, 9411, 4451, 9258, QCVN 10, QCVN 04-3, building orientation, heat protection, microclimate.

To do: re-upload `thiet-ke-phong-nha.zip` to Claude Desktop (Settings, Skills).

Known limitations:

- The figures were read from the Word versions of the standards; drawings could not be read, so every "see Figure ..." clause needs the original.
- Items to check against the original: the line "window area not less than 60 %" in TCVN 9258 (8.6.4) does not say 60 % of what; the humidity column of TCVN 14214; the "0.09 m" attic stair width in TCVN 4451 (probably 0.90 m); the corner-cut table for corner houses in TCVN 9411.
- These are reference standards. Detailed planning, local architecture rules, QCVN 06 (fire safety) and the project brief take precedence when stricter.
- The skill has not been run on a real floor plan in a DWG.
- Carried over from v0.2.7: the Revit pyRevit tab has not been tried against a running Revit; the inventory (`entity inventory`) does not see a pure move while it is cached; the gateway (port 8764) does not start by itself after Windows restarts; the Windows installer is unsigned.
