---
name: autocad-agent-coordinator
description: Điểm vào BẮT BUỘC cho mọi việc AutoCAD qua MCP autocad_beiming và autocad_puran - vẽ, sửa, đọc, đo, kiểm tra, chép, xuất bản vẽ CAD, vẽ layout, mặt bằng, tổng mặt bằng, ranh đất. Nạp trước khi gọi bất kỳ tool CAD nào. Chứa bảng chọn skill chuyên biệt theo lời người dùng, quy tắc xác nhận khu đất bằng ảnh trước khi lập kế hoạch layout, quy tắc hỏi lại khi yêu cầu mơ hồ, và quy ước màu, giới hạn của AutoCAD LT.
---

# Điều phối agent làm việc với AutoCAD

Đây là điểm vào của mọi công việc AutoCAD thực hiện qua ứng dụng kết nối MCP của dự án: nạp skill này trước khi gọi bất kỳ tool CAD nào. Skill hướng dẫn agent; các công cụ MCP mới thực hiện thao tác CAD. Không nói rằng việc nạp skill đã mở AutoCAD hoặc kết nối MCP.

## Chọn skill theo yêu cầu (đọc trước khi gọi tool CAD)

Skill chỉ có tác dụng khi được nạp. Ngay sau khi nhận yêu cầu AutoCAD, đối chiếu bảng dưới, **nạp bằng công cụ Skill mọi skill khớp** rồi mới thao tác; không làm theo trí nhớ. Skill không có trong danh sách của môi trường thì đọc thẳng tệp `skills/<tên>/SKILL.md` (thư mục `.claude`, `.codex` hoặc `.agents` của dự án hoặc của tài khoản). Yêu cầu khớp nhiều hàng thì nạp các skill theo thứ tự từ trên xuống.

| Người dùng nói hoặc tình huống | Nạp skill |
|---|---|
| "vẽ layout", "bố trí mặt bằng", "tổng mặt bằng", "phương án", kèm mặt bằng hoặc bản vẽ nền | Quy tắc 1 bên dưới, rồi `autocad-identify-and-measure` (đọc `references/boundaries.md`), `construction-boundaries-grids`, `autocad-verify-drawing-inputs`, `autocad-start-construction-drawing` |
| "ranh đất", "khu đất", "đâu là tòa nhà", "đường bao", "chỉ giới", "khoảng lùi" | `autocad-identify-and-measure`, `construction-boundaries-grids` |
| "mặt bằng tổng thể", "MBTT", "tổng mặt bằng", "bảng chỉ tiêu", "cân bằng đất đai", "bản vị trí khu đất" | Quy tắc 1 bên dưới, `mat-bang-tong-the`, rồi `autocad-identify-and-measure`, `construction-boundaries-grids` |
| "đo", "kích thước", "diện tích", "khoảng cách", "cột/tường/dầm/cửa này", "phần bị che" | `autocad-identify-and-measure` |
| "vẽ lại", "dựng lại", "vẽ theo bản này/PDF này" (có bản tham chiếu) | `autocad-redraw-from-reference` |
| "tạo giống", "thêm một ... như ...", "làm tương tự", "lặp lại", "chép sang", "copy sang bản vẽ khác" | `autocad-copy-similar-objects` |
| nội thất, giường, bàn ghế, tủ, toilet/bồn cầu, bếp, cửa đi, cửa sổ, cây, xe, ký hiệu, "chèn block", "dùng block có sẵn" | `autocad-block-library` |
| "mặt bằng kết cấu", "bố trí dầm sàn cột", "mặt bằng dầm", "vẽ dầm/cột tầng ..." | `autocad-structural-floor-plan`, `autocad-structural-drawing` |
| bản vẽ móng, mặt cắt, chi tiết kết cấu, thuyết minh bản vẽ kết cấu | `autocad-structural-drawing` |
| "viền sàn", "đường bao tầng", "tường rời chưa khép kín", "truy biên" | `autocad-trace-floor-outline` |
| "kiểm tra hồ sơ/số liệu/phiên bản trước khi vẽ", "đã đủ căn cứ chưa", bản vẽ nền không rõ phiên bản | `autocad-verify-drawing-inputs` |
| bắt đầu bản vẽ xây dựng mới, layer, đơn vị, hệ trục, Layout, in | `autocad-start-construction-drawing` |
| "nét vẽ", "đường trục", "TCVN 5570", kiểu và bề rộng nét | `construction-drawing-tcvn5570` |
| thiết kế cơ sở, thiết kế kỹ thuật, bản vẽ thi công, chưa rõ đang ở bước nào | `construction-document-router`, rồi `construction-design-stages` |
| bản vẽ phát hành, cập nhật theo hiện trường, thay đổi khi thi công | `construction-drawing-records` |

Sau khi nạp, nói ngắn cho người dùng đã nạp skill nào và vì sao (một dòng trong thông báo cách làm).

## Quy tắc 1: vẽ layout từ mặt bằng thì xác nhận khu đất bằng ảnh trước khi lập kế hoạch

Áp dụng khi người dùng yêu cầu vẽ layout, bố trí mặt bằng, tổng mặt bằng hoặc phương án và đưa mặt bằng làm căn cứ (bản vẽ đang mở, tệp DWG/DXF, PDF hoặc ảnh). **Chưa được lập kế hoạch, chưa được đặt số liệu và chưa được vẽ cho đến khi người dùng xác nhận khu đất.**

1. **Xác định khu đất (chỉ đọc).** Xác nhận đúng bản vẽ đang hoạt động (chuyển bằng `drawing` `activate` nếu cần). Làm theo [autocad-identify-and-measure](../autocad-identify-and-measure/references/boundaries.md): tìm ranh bằng layer, màu, đường kín, tên layer như `A-SITE-PROP`; lấy tập đối tượng trong ranh; ghi đơn vị, số góc, chu vi, diện tích và mức chắc chắn (cao, vừa, thấp). Không lấy ranh từ khung bao (bounding box).
2. **Chụp lại.** Phóng vào khu đất kèm lề bằng `view` `operation="zoom_window"` (`x1`, `y1`, `x2`, `y2`), rồi `view` `operation="get_screenshot"` (`data.include_image=true`). Ảnh lưu ở `payload.screenshot.path`; đọc ảnh đó để kiểm tra có thấy ranh rõ không và đưa đường dẫn đầy đủ cho người dùng. Nếu chụp lỗi (`Screenshot capture failed`), nói rõ và thay bằng bảng số (tọa độ các góc, diện tích, layer, handle) rồi nhờ người dùng nhìn vào tab AutoCAD. Phóng thay đổi khung nhìn, không đổi bản vẽ; nói trước.
3. **Hỏi xác nhận một lần**, kèm ảnh và bảng số, đúng ba lựa chọn: **Đúng**, **Sai** (người dùng chỉ ranh bằng layer, màu, đối tượng mẫu hoặc vẽ khoanh), **Đúng một phần** (nói phần nào sai). Nêu ranh nào nghi là ranh đất nhưng chưa chắc, ranh nào là đường bao nhà, và khối nhà nào đã bị loại. Hỏi bằng công cụ chọn (xem mục "Cách hỏi"), không liệt kê ba lựa chọn bằng văn bản.
4. **Chờ trả lời.** Chỉ khi người dùng xác nhận *Đúng* mới qua bước lập kế hoạch (thông báo cách làm theo mục "Quy trình", rồi các skill dựng hình ở bảng trên). Trả lời *Sai* hoặc *Đúng một phần* thì quay lại bước 1 với chỉ dẫn mới và chụp lại. Việc chỉ đọc khác vẫn làm được trong lúc chờ.
5. **Ghi lại ranh đã xác nhận** (handle hoặc tọa độ các góc, diện tích, đơn vị, bản vẽ) trong kế hoạch và báo cáo cuối. Cùng bản vẽ trong cùng phiên đã xác nhận rồi thì không hỏi lại; bản vẽ khác, ranh bị sửa, hoặc người dùng đổi yêu cầu về phạm vi đất thì xác nhận lại.

Quy tắc này bổ sung cho Quy tắc 2, không thay thế: sau khi khu đất được xác nhận, yêu cầu vẫn mơ hồ ở chỗ khác thì hỏi theo Quy tắc 2.

## Quy tắc 2: yêu cầu mơ hồ thì hỏi trước khi làm

Ngay khi nhận yêu cầu, trước mọi thao tác sửa bản vẽ, kiểm tra yêu cầu đã đủ để làm chưa. Yêu cầu **mơ hồ** khi một trong các điều sau đúng:

- thiếu số liệu quyết định hình vẽ (kích thước, vị trí, cao độ, tiết diện, số lượng) mà bản vẽ đang mở và tài liệu người dùng đưa cũng không cho biết;
- chưa rõ đối tượng, bản vẽ đích, tầng hoặc khu vực;
- có hơn một cách hiểu hợp lý và chúng cho hình vẽ khác nhau.

Khi mơ hồ, **dừng và hỏi người dùng một lần**, đưa đúng hai lựa chọn:

1. **Người dùng cung cấp thêm số liệu:** nêu cụ thể cần số nào (liệt kê ngắn, nhóm trong một lượt, không hỏi lại điều đã có).
2. **Agent tự vẽ theo giả định:** nêu luôn giả định sẽ dùng (giá trị, nguồn hoặc lý do) để người dùng đồng ý hoặc sửa.

Chờ người dùng chọn rồi mới vẽ. Không tự chọn một trong hai và không tự đặt số liệu "hợp lý" khi chưa được phép. Nếu người dùng chọn để agent tự vẽ, ghi mọi giả định vào danh sách `CẦN XÁC NHẬN` ở báo cáo cuối. Phần việc độc lập đã đủ căn cứ và thao tác chỉ đọc vẫn làm được trong lúc chờ.

## Cách hỏi: dùng công cụ chọn, không liệt kê lựa chọn bằng văn bản

Mọi câu hỏi có vài lựa chọn rời rạc (xác nhận ranh đất đúng/sai, hai lựa chọn của Quy tắc 2, số tầng hầm, phương án khối, chọn bản vẽ đích) phải hỏi **ngay lần đầu** bằng công cụ hỏi có lựa chọn của môi trường (`AskUserQuestion` trong Claude Code), để người dùng bấm chọn. Không viết "Đúng / Sai / Đúng một phần" thành danh sách trong tin nhắn rồi chờ gõ trả lời.

- Công cụ chỉ nhận chữ, không hiển thị ảnh: gửi ảnh, đường dẫn ảnh và bảng số trong tin nhắn ngay trước, rồi gọi công cụ trong cùng lượt.
- Nhóm tối đa vài câu liên quan vào một lần gọi; mỗi câu 2–4 lựa chọn, ghi rõ hệ quả của từng lựa chọn. Người dùng luôn có thể nhập ý khác.
- Chỉ hỏi bằng văn bản khi môi trường không có công cụ chọn (ví dụ một số máy khách khác), hoặc khi câu trả lời là số liệu tự do.

Các skill khác (`autocad-verify-drawing-inputs`, `autocad-structural-floor-plan`, `autocad-redraw-from-reference`, `autocad-block-library`) quy định thêm điểm chặn riêng cho loại bản vẽ của chúng; Quy tắc 1 và Quy tắc 2 luôn áp dụng trước.

Không cần hỏi lại, agent tự quyết: layer và màu theo quy ước bản vẽ, chiều cao chữ, thứ tự dựng, chọn block theo tên thư viện khi mô tả khớp rõ một mục.

## Nhận diện ranh đất và khối nhà

Khi cần xác định ranh khu đất, chọn khối tòa nhà, phân biệt tường ngoài/mép sàn/mái hoặc khoanh phạm vi trước khi đo, chép hay vẽ tiếp, đọc và áp dụng [autocad-identify-and-measure](../autocad-identify-and-measure/references/boundaries.md) nếu skill có trong môi trường agent.

Ưu tiên tìm ranh đất rồi lấy toàn bộ đối tượng bên trong làm tập ứng viên; giữ riêng đối tượng chạm/cắt ranh, sau đó lọc hoặc nhờ người dùng xác nhận nhóm thuộc tòa nhà. Nếu chưa tìm được ranh, hỏi màu, layer, vị trí hoặc đối tượng mẫu. Tập ứng viên trong ranh có thể chứa sân, đường và ghi chú; chưa coi tất cả là đường bao nhà đã xác minh. Kiểm tra đúng DWG và phạm vi trước khi tái dùng kết quả nhận diện.

Nếu skill chưa được cài, áp dụng quy trình tóm tắt trên bằng các tool thực tế đang có và nói rõ điểm chưa xác định. Skill nhận diện không tự bổ sung tool MCP; chỉ sửa/chép khi nằm trong yêu cầu của người dùng.

## Bắt đầu bản vẽ xây dựng

Trước khi tạo hoặc sửa bản vẽ theo hồ sơ đầu vào, đọc và áp dụng [autocad-verify-drawing-inputs](../autocad-verify-drawing-inputs/SKILL.md) để kiểm tra đúng phiên bản, đơn vị, định vị và các dữ liệu còn thiếu. Nếu có thông tin chặn, hỏi rõ trước phần phụ thuộc; nếu chỉ còn giả định cho phương án sơ bộ, nêu chúng cho người dùng.

Khi người dùng muốn tạo mặt bằng hoặc bắt đầu dựng bản vẽ xây dựng 2D từ căn cứ thiết kế, đọc và áp dụng [autocad-start-construction-drawing](../autocad-start-construction-drawing/SKILL.md) nếu skill có trong môi trường agent. Skill này hướng dẫn kiểm tra đầu vào, đơn vị, layer, hệ trục, hình học, chữ/kích thước và tờ in trước khi kết luận hoàn thành. Nếu skill chưa được cài, giữ trình tự đó và dùng các tool MCP thực tế đang có.

## Thư viện block (nội thất, cây cối, cửa, thiết bị)

Khi cần tạo một vật thể thông dụng trên AutoCAD LT (nội thất, thiết bị vệ sinh và bếp, cửa, cửa sổ, cây, ngoại thất, ký hiệu bản vẽ, thép hình), đọc và áp dụng [autocad-block-library](../autocad-block-library/SKILL.md) trước khi vẽ tay: gọi `block` `operation="list"`, chọn mục trong `library`, tính điểm chèn từ `bbox_mm`, chèn bằng `operation="insert"` với `scale` bằng 1, rồi đọc lại `xscale` (phải bằng `scale` nhân `scale_factor` của mục). Chỉ vẽ tay khi thư viện và danh mục không có vật thể phù hợp. Skill này không có trong môi trường thì dùng `block` `list` và áp dụng các bước trên.

## Quy trình

1. Xác định kết quả người dùng cần, bản vẽ sẽ tác động và bộ môn của công việc. Dùng công cụ chỉ đọc để kiểm tra các MCP sẵn có và trạng thái bản vẽ hiện tại. Với bản vẽ xây dựng như kiến trúc, kết cấu, dùng `autocad_beiming`. Chỉ dùng `autocad_puran` cho bản vẽ MEP như điện, điều hòa, cấp thoát nước và các hệ kỹ thuật liên quan. Nếu yêu cầu gồm cả xây dựng và MEP, tách phần việc theo bộ môn rồi chọn MCP tương ứng cho từng phần. Gateway sẽ đổi kết nối khi gọi công cụ. Thử AutoCAD trước; nếu công cụ trả `AUTOCAD_UNAVAILABLE`, hỏi người dùng: “AutoCAD hiện không chạy. Bạn có muốn tôi xuất bản vẽ dạng DXF thay thế không?” Chờ câu trả lời rõ ràng; chỉ khi được đồng ý mới gọi `launcher_set_backend` với `mode="ezdxf", user_confirmed=true`. Nếu người dùng không đồng ý, dừng thao tác và chờ AutoCAD.
2. Trước thao tác đầu tiên làm thay đổi bản vẽ, thông báo ngắn gọn cho người dùng: bản vẽ hoặc khu vực nào sẽ thay đổi, sẽ làm gì và sẽ kiểm tra kết quả ra sao. Nếu công việc có nhiều bước, liệt kê các bước chính. Đây là thông báo cách làm; chỉ hỏi phê duyệt khi nhiệm vụ hoặc môi trường agent thực sự yêu cầu.
3. Thực hiện bằng các công cụ mà MCP đã chọn thực sự cung cấp. Đọc cấu trúc tham số của từng công cụ trước khi gọi. Khi tạo đối tượng, kiểm tra layer và áp dụng quy ước màu của bản vẽ theo mục dưới đây. Thực hiện các thao tác sửa CAD theo thứ tự. Không tự giả định có khả năng giao dịch, hoàn tác, đọc lại hay xuất tệp nếu công cụ hiện dùng không cung cấp. Nếu cách làm thay đổi đáng kể, thông báo trước khi tiếp tục.
4. Sau mỗi thay đổi quan trọng, dùng công cụ chỉ đọc sẵn có để so trạng thái bản vẽ thực tế với yêu cầu. Nếu lệnh lỗi hoặc kết quả không rõ, dừng các bước phụ thuộc, báo lỗi cụ thể và chưa kết luận đã hoàn thành.
5. Kết thúc bằng báo cáo ngắn: đã thay đổi gì, đã kiểm tra gì và điểm nào còn chưa chắc chắn. Phân biệt lệnh chạy thành công với việc đã xác minh bản vẽ đúng yêu cầu.

### Đọc bản vẽ và theo dõi thay đổi

Khi cần nắm cấu trúc bản vẽ qua Beiming, gọi `drawing` với `operation="audit"`; dùng `include_entities=false` nếu chỉ cần tóm tắt. `changed_only=true` trả các đối tượng thay đổi so với lần audit trước của cùng bản vẽ trong cùng tiến trình MCP và cùng phạm vi. Bỏ tùy chọn này nếu cần toàn bộ đối tượng. Khi chuyển sang bản vẽ khác, baseline được tách riêng; sau khi có thay đổi mà kết quả chưa xác nhận được, đọc lại trước khi kết luận.

Với DWG lớn, bắt đầu bằng một lần audit Model Space với `include_entities=false` để lấy tổng số và số lượng theo layer; sau đó chỉ audit các layer ứng viên cần kiểm tra, tuần tự. Không giả định audit theo layer dùng snapshot đã cache: trong cấu hình COM-only hiện tại, Beiming không báo revision từ database event và mỗi audit có thể quét lại Model Space. Audit chỉ trả tối đa 500 entity; nếu có `truncated=true`, mẫu đó chưa đủ để khẳng định đã kiểm tra hết. Tránh gọi `entity.list` hoặc `entity.get` lặp cho hàng trăm đối tượng và không gửi nhiều lệnh đọc CAD song song. Chỉ tái sử dụng cache khi kết quả/cấu hình xác nhận cache hit và đúng bản vẽ, revision.

## Quy ước màu của bản vẽ hiện tại

Áp dụng bảng này khi vẽ hoặc chỉnh sửa **bản vẽ đang dùng quy ước này**. Trước khi tạo đối tượng, đọc layer và màu đang có trong DWG; nếu bản vẽ khác dùng quy ước khác, theo quy ước của bản vẽ đó hoặc hỏi người dùng. Ưu tiên đặt màu đối tượng là `ByLayer` và đặt ACI cho layer tương ứng. Không đổi màu hàng loạt các đối tượng sẵn có chỉ để khớp bảng này. Khi sao chép giữa các DWG, giữ nguyên layer và màu nguồn, trừ khi người dùng yêu cầu chuyển sang quy ước của DWG đích.

| ACI | Màu tham chiếu | Đối tượng / layer |
|---:|---|---|
| 1 | Đỏ `#FF0000` | Tường, đường bao, kính và đố kính, cầu thang, đường dốc, lan can, đường kích thước và số đo. |
| 2 | Vàng `#FFFF00` | Cửa đi, khung cửa, nét biểu diễn cửa mở. |
| 3 | Xanh lá `#00FF00` | Tên phòng, diện tích, cao độ, vòng tròn và chữ/số trục định vị, ký hiệu tham chiếu. |
| 4 | Xanh lơ `#00FFFF` | Cột kết cấu, layer `S-COLS`. |
| 6 | Tím hồng `#FF00FF` | Ranh khu đất, layer `A-SITE-PROP`. |
| 7 | Trắng `#FFFFFF` trên nền tối | Chữ ghi chú, mũi tên, một số hatch và chi tiết phụ. |
| 8 | Xám `#808080` | Đường trục định vị, nội thất, thiết bị vệ sinh, tủ và một số chi tiết cửa. |
| 10 | Đỏ `#FF0000` | Layer `003-wall` đã khai báo; chưa thấy đối tượng trực tiếp trong Model. Chỉ dùng nếu thực sự vẽ trên layer này. |
| 11 | Hồng nhạt `#FF7F7F` | Hatch cột `S-COLS-PATT`; layer hatch tường `A-FLOR-WALL-PATT` cũng khai báo màu này. |

ACI là mã màu cần truyền cho AutoCAD khi công cụ nhận ACI; HEX/RGB chỉ để nhận biết màu. ACI 1 và ACI 10 cùng đỏ trên màn hình nhưng là hai chỉ số khác nhau, có thể in khác nhau theo CTB. ACI 7 đổi cách hiển thị theo nền AutoCAD. Đường trục hình học dùng ACI 8; vòng tròn và chữ/số nhãn trục dùng ACI 3. Với chi tiết cửa có cả ACI 2 và 8, đọc layer và đối tượng cùng loại trong bản vẽ trước khi chọn. Trước khi xuất/in, kiểm tra CTB/STB và bản xem trước; màu hiển thị không quyết định bề rộng nét in.

## Công cụ nào dùng được trên AutoCAD LT

- Trước khi kết luận một công cụ không dùng được trên LT, gọi thao tác chỉ đọc của nó (preview, list, info) và đọc mã lỗi trả về. Chỉ kết luận theo lỗi đã quan sát được, không theo suy đoán.
- Khi cần đọc mã nguồn để biết hành vi trên LT, xem `lt-adapter/` trước (`contract.json`, `py/lt_adapter/`, `lisp/mcp_dispatch_lt.lsp`). Không suy ra từ `autocad-beiming-mcp-custom/`: đó là mã gốc cho AutoCAD đầy đủ, adapter thay thế nhiều phần của nó khi chạy trên LT.
- `copy_region_between_dwgs` và `delete_batching` đã được thay bằng bản LT và dùng được trên LT. `copy_region_between_dwgs` cần hai file DWG đã lưu, cả hai đang mở trong cùng một phiên LT, bản nguồn phải là bản vẽ đang hoạt động; chuyển bằng `drawing` `activate` (xem dưới), không cần nhờ người dùng bấm tab.
- `drawing` `activate` dùng được trên LT cho bản vẽ **đã mở sẵn** trong phiên: truyền `doc_id` (hoặc đường dẫn đầy đủ của file) và `expected_revision`. Nếu `doc_id` không thuộc bản vẽ nào đang mở, lỗi trả về kèm `open_documents` (đường dẫn, tên, bản nào đang hoạt động). Sau khi chuyển, đọc lại `drawing` `context` vì `doc_id`, `revision` và `lease_token` thuộc bản vẽ mới. `drawing` `open` với đường dẫn đầy đủ (có thể có dấu tiếng Việt) mở được file DWG/DXF có sẵn trên LT và đưa nó thành bản vẽ đang hoạt động; đường dẫn sai trả `DWG file not found`. Sau khi mở, đọc lại `drawing` `context` để xác nhận đúng tên bản vẽ trước khi vẽ. LT không tạo bản vẽ mới và không đóng bản vẽ: cần file mới thì nhờ người dùng tạo, hoặc xin phép chép một bản mẫu thành file mới rồi mở nó.
- **Tạo bản vẽ mới trên LT: làm như tạo một file DWG bình thường.** `drawing create` không chạy trên LT, nên: (1) hỏi người dùng tên file và thư mục lưu (hộp chọn nếu có vài phương án); (2) sao một template của LT thành file `.dwg` ở đó, ví dụ `acadltiso.dwt` (mm) trong `%LOCALAPPDATA%\Autodesk\AutoCAD LT <năm>\R<số>\enu\Template\` (tìm `*.dwt` nếu thư mục khác), dùng lệnh sao chép của hệ điều hành, không ghi đè file có sẵn; (3) `drawing` `open` file đó, rồi `drawing` `context` để lấy `doc_id`. Template đã có sẵn Layout1, Layout2, đơn vị và kiểu chữ, kích thước. Không tự dựng file DXF hay DWG tối giản bằng mã để thay cho template, vì file đó thiếu Layout, đơn vị (`INSUNITS`=0) và kiểu chú thích. Xong việc, hỏi người dùng rồi lưu bằng `drawing` `save` (mục dưới).
- **Lưu bản vẽ trên LT: hỏi người dùng rồi mới lưu.** Hỏi bằng công cụ chọn (mục "Cách hỏi"): lưu đè file hiện tại, lưu thành bản mới ở nơi người dùng chỉ, hoặc để người dùng tự lưu. Rồi gọi `drawing` `operation="save"` kèm `doc_id`, `expected_revision`, `lease_token`, `worker_generation` trong `data`. Lưu tại chỗ: không đưa `path`. Lưu bản mới: `data.path` là đường dẫn đầy đủ tận cùng `.dwg` ở thư mục đã có; bản vẽ đang mở chuyển sang file mới. File đích đã tồn tại thì lệnh trả `E_FILE_EXISTS`; chỉ gửi lại với `data.overwrite=true` sau khi người dùng đồng ý thay file đó. Không bao giờ tự đặt `overwrite`. Báo thành công chỉ khi kết quả có `dbmod` bằng 0; nếu không, nói rõ bản vẽ chưa lưu. Lưu DXF (`save_as_dxf`) vẫn không hỗ trợ.
- Không hỗ trợ trên LT (trả `E_NOT_SUPPORTED_ON_LT`): `drawing` các thao tác `create`, `close`, `copy_dwg`, `save_as_dxf`, `plot_pdf`, `audit`, `render_preview`; `recover`; `zoom_extents`; `entity` các thao tác `trim`, `extend`, `join`; `create_dimension_*`; `solid_*`; `product_*`. Nguồn danh sách: `_UNSUPPORTED` trong `lt-adapter/py/lt_adapter/lt_file_ipc.py`; đối chiếu lại khi nghi ngờ.

## Giới hạn

- Việc nạp hoặc gọi skill không chứng minh rằng công cụ đã chạy. Chỉ báo cáo kết quả đã quan sát được.
- Không tự tạo tên thao tác MCP hoặc dùng tham số ví dụ như thể đó là cấu trúc tham số được hỗ trợ.
- Không sửa đối tượng ngoài phạm vi yêu cầu hoặc âm thầm đổi bản vẽ đang hoạt động. Làm rõ bản vẽ đích nếu có thể tác động đến nhiều bản vẽ.
- Không chọn `autocad_puran` cho bản vẽ xây dựng chỉ vì công cụ của nó thuận tiện hơn. Nếu chưa rõ bộ môn, làm rõ hoặc kiểm tra bản vẽ bằng thao tác chỉ đọc trước khi chọn MCP để sửa.
- **Chỉ tạo file DXF khi người dùng yêu cầu, hoặc khi không có kết nối AutoCAD.** Tạo DXF gồm `drawing.save_as_dxf`, chuyển sang backend `ezdxf`, xuất bản sao DXF để phân tích hay để đổi định dạng. Khi AutoCAD đang kết nối, làm việc trực tiếp trên bản vẽ DWG đang mở; không tự xuất DXF "cho tiện", kể cả bản sao để phân tích. Cần bản sao DXF để phân tích mà người dùng chưa yêu cầu thì hỏi trước bằng công cụ chọn. Khi không có kết nối AutoCAD (gateway báo AutoCAD không chạy hoặc chưa mở bản vẽ, hoặc MCP AutoCAD không kết nối): nói rõ tình trạng, hỏi người dùng đồng ý xuất DXF thay thế (gateway chỉ chuyển sang `ezdxf` khi `user_confirmed=true`), và nhắc DXF không phải DWG.
- Backend `ezdxf` chỉ tạo hoặc mở DXF, không tạo DWG. Gọi `drawing.save` để lưu DXF trước khi đổi MCP hoặc quay lại AutoCAD. Khi người dùng muốn quay lại AutoCAD, gọi `launcher_set_backend` với `mode="autocad"` rồi thử tool.
- Skill yêu cầu agent giải thích trước khi thao tác. Nếu môi trường chạy cần bắt buộc mọi agent tuân theo thứ tự này, môi trường đó cũng phải chặn thao tác sửa CAD ở bên ngoài skill.

## Ví dụ thông báo cách làm

"Tôi sẽ kiểm tra bản vẽ đang mở, tạo các đối tượng theo kích thước bạn đưa trên đúng layer, rồi đọc lại tọa độ và số lượng đối tượng để xác nhận. Nếu bản vẽ hoặc kích thước chưa rõ, tôi sẽ hỏi trước khi sửa."
