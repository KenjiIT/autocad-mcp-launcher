AutoCAD MCP Launcher v0.2.4

# Tiếng Việt

Thêm:

- Skill mới `mat-bang-tong-the`: dựng và rà soát mặt bằng tổng thể (MBTT), gồm xác nhận khu đất bằng ảnh, mô hình 3D phương án khối đủ chi tiết (vạch tầng, đế và hầm, mái đế có hồ bơi và cây, nền đường, chỉ giới), bảng thuyết minh từng phương án (tổng số căn hộ, số căn từng loại, diện tích từng loại, số căn mỗi tầng, danh sách khu tiện ích, đối chiếu với GFA) và bảng chỉ tiêu.
- Launcher: tab Revit (thử nghiệm) để quản lý kết nối Revit MCP.

Sửa:

- AutoCAD LT: lỗi nạp dispatcher không còn làm lệnh đầu tiên thất bại; hệ thống tự thử lại khi dispatcher chưa nạp xong (có thêm test).
- Skill `autocad-agent-coordinator`, `autocad-structural-floor-plan` và `AGENTS.md`: câu hỏi có vài lựa chọn rời rạc (xác nhận ranh đất, số tầng hầm, phương án) phải hiện bằng giao diện chọn ngay lần hỏi đầu, không liệt kê lựa chọn bằng văn bản.

Giới hạn đã biết:

- Tab Revit chưa được thử trên Revit thật.
- Skill `mat-bang-tong-the` chưa được chạy thử trọn vẹn với một phương án thật; mô hình 3D chi tiết mới được mô tả trong skill, chưa dựng lại cho dự án mẫu.
- Việc agent dùng giao diện chọn phụ thuộc vào client có công cụ hỏi có lựa chọn hay không; nếu không, agent quay về hỏi bằng văn bản.
- AutoCAD LT vẫn không tự lưu bản vẽ; người dùng phải lưu thủ công.
- Kế thừa từ v0.2.3: bộ cài Windows chưa ký, SmartScreen có thể cảnh báo nhà phát hành không xác định.

# English

Added:

- New skill `mat-bang-tong-the`: builds and reviews site master plans (MBTT), including lot confirmation by screenshot, a detailed 3D massing model (floor lines, podium and basement, podium roof with pool and trees, roads, setback lines), a per-option description table (total apartments, count and area per type, apartments per floor, amenity list, reconciliation with GFA) and an indicator table.
- Launcher: experimental Revit tab to manage the Revit MCP connection.

Fixed:

- AutoCAD LT: a dispatcher load error no longer fails the first command; the adapter retries while the dispatcher is still loading (tests added).
- Skills `autocad-agent-coordinator`, `autocad-structural-floor-plan` and `AGENTS.md`: questions with a few discrete choices (lot confirmation, number of basements, design option) must show the choice UI at the first ask instead of listing options as text.

Known limitations:

- The Revit tab has not been tried on real Revit.
- Skill `mat-bang-tong-the` has not been run end to end on a real option; the detailed 3D model is described in the skill but has not been rebuilt for the sample project.
- Whether the agent shows the choice UI depends on the client having a choice tool; otherwise it falls back to a text question.
- AutoCAD LT still cannot save drawings; the user must save manually.
- Carried over from v0.2.3: the Windows installer is unsigned; SmartScreen may show an unknown publisher warning.
