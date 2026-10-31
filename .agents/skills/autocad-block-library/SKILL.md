---
name: autocad-block-library
description: Tra và chèn block dựng sẵn thay vì vẽ tay - nội thất (giường, bàn, ghế, tủ, sofa), thiết bị vệ sinh (toilet, bồn cầu, lavabo), thiết bị bếp, cửa đi, cửa sổ, cây cối, xe, ngoại thất, ký hiệu bản vẽ, thép hình; kèm danh mục 432 block của bản vẽ mẫu AutoCAD LT và các kho riêng của người dùng (ví dụ kho `dwgshare`: sofa, bàn, văn phòng, bếp - phòng ngủ - vệ sinh, cây, cầu thang). Dùng khi người dùng cần bố trí hoặc thêm một vật thể thông dụng, hoặc nói 'chèn block', 'dùng block có sẵn'. Gọi trước khi định vẽ tay một vật thể.
---

# Thư viện block AutoCAD

Khi bản vẽ cần một vật thể thông dụng (giường, sofa, bàn, bồn cầu, lavabo, bếp, cửa, cửa sổ, cây, hồ bơi, xe, mũi tên hướng bắc, ký hiệu cao độ...), **tra thư viện và chèn block có sẵn**, không vẽ tay từng nét. Chỉ vẽ tay khi thư viện không có vật thể phù hợp.

Thư viện là thư mục `blocks/` của dự án (hoặc thư mục trong biến `AUTOCAD_MCP_BLOCK_LIBRARY`). Mỗi tệp `.dwg` là một block; tên tệp là tên block. Launcher có nút **Mở thư mục thư viện** trong tab Cài đặt. Danh mục đầy đủ nằm ở [references/catalog.md](references/catalog.md).

## Quy trình lấy block thay vì vẽ

1. **Xác định vật thể:** là gì, nhìn từ đâu (mặt bằng, mặt đứng hay ký hiệu), kích thước cần, đặt ở đâu và hướng nào. Bản vẽ mặt bằng dùng block loại *mặt bằng*; chỉ dùng loại *mặt đứng* khi vẽ mặt đứng hoặc mặt cắt.
2. **Tra thư viện:** gọi `block` với `operation="list"`. Trường `library` liệt kê mỗi tệp với `meaning` (ý nghĩa), `view`, `size_mm` (rộng x sâu), `bbox_mm` (khung bao so với điểm chèn), `scale_factor`, `units`. Chọn mục có ý nghĩa và kích thước gần nhất. Cần tìm rộng hơn thì đọc [references/catalog.md](references/catalog.md), nơi liệt kê cả block chưa tách thành tệp. Không có mục phù hợp ở `library` thì tra các **kho riêng** (mục dưới), trước khi vẽ tay.
3. **Tính điểm chèn.** Điểm chèn của block là gốc (0,0) của chính nó và **không nằm ở giữa**. `bbox_mm = [x1, y1, x2, y2]` cho biết hình nằm ở đâu quanh gốc (mm, tỉ lệ 1, góc xoay 0). Ví dụ `SANI-WC-PLAN` có `y` từ -838 đến 0: gốc ở mép sau giữa, tức đặt gốc lên mặt tường là bồn cầu áp tường.
   - Muốn tâm khung bao rơi vào điểm (cx, cy) khi xoay 0: chèn tại x = cx − (x1+x2)/2, y = cy − (y1+y2)/2.
   - Khi có xoay góc θ (độ, ngược chiều kim đồng hồ): lấy vectơ tâm c = ((x1+x2)/2, (y1+y2)/2); điểm chèn = (cx, cy) − R(θ)·c, với R(θ) quay vectơ một góc θ.
   - Muốn áp một cạnh vào tường: đặt gốc (hoặc cạnh của khung bao) lên đường tường rồi chọn θ để mặt trước hướng ra phía phòng.
4. **Chèn:** gọi `block` với `operation="insert"`, `data={"name": <tên tệp bỏ đuôi>, "x": ..., "y": ..., "scale": 1, "rotation": θ}`. Giữ `scale` bằng 1: kích thước thật đã nằm trong tên (`FURN-BED-QUEEN-1525x2030` rộng 1525 mm, sâu 2030 mm). Chỉ đổi `scale` khi người dùng yêu cầu kích thước khác.
5. **Kiểm sau khi chèn:** đọc lại bằng `entity` `get`. `xscale` phải bằng `scale` × `scale_factor` của mục thư viện. Tệp inch chèn vào bản vẽ mm có `scale_factor` 25.4, nên `xscale` 25.4 là đúng, AutoCAD tự quy đổi đơn vị. Nếu `scale_factor` là `null` (tệp không biết đơn vị) hoặc `xscale` khác dự kiến thì đo lại khung bao của đối tượng; sai kích thước thì xóa đối tượng vừa chèn và báo người dùng.
6. **Layer và màu:** đối tượng `INSERT` mang layer hiện hành. Chọn layer nội thất/thiết bị đang có trong bản vẽ và theo quy ước màu của `autocad-agent-coordinator`. Hình bên trong 101 trong 105 block nằm hết trên layer `0`, nên block theo layer của đối tượng `INSERT`. Bốn block động (`CIVIL-PARKING-STALL`, `DOOR-DYN-ELEV`, `ELEC-LIGHT-RECESSED-DYN`, `STRUC-CHANNEL`) có thêm layer nội bộ `*ADSK_CONSTRAINTS` của ràng buộc động; bỏ qua. Màu của từng nét bên trong (ByLayer hay cố định) chưa được kiểm.

Không có block phù hợp: nếu danh mục có mà chưa tách thành tệp, báo người dùng và đề nghị tách (mục *Dựng lại thư viện*). Nếu danh mục cũng không có, áp dụng quy tắc hỏi trước của `autocad-agent-coordinator`: hỏi người dùng cung cấp kích thước hoặc đồng ý để agent tự vẽ theo giả định nêu rõ; chỉ vẽ tay khi đã có kích thước hoặc được đồng ý. Không tự bịa tên block.

## Các nhóm trong thư viện

Tên tệp có dạng `<NHÓM>-<LOẠI>[-<BIẾN THỂ>]-<RỘNG>x<SÂU>` (mm). Hiện có 105 tệp:

| Nhóm | Số tệp | Nội dung | Ví dụ |
|---|---|---|---|
| `KITCH` | 21 | Thiết bị và tủ bếp: bếp, tủ lạnh, bồn rửa, tủ trên/dưới, bố trí bếp 7x8 ft | `KITCH-CAB-BASE-FRONT-610x875`, `KITCH-CAB-BASE-SIDE-610x875`, `KITCH-CAB-WALL-FRONT-915x455` |
| `FURN` | 19 | Nội thất: giường, sofa, bàn, ghế, tủ, đàn piano | `FURN-BED-QUEEN-1525x2030`, `FURN-CHAIR-DESK-535x430`, `FURN-CHAIR-ROCKING-615x675` |
| `PLANT` | 10 | Cây cối: cây tán tròn mặt bằng, cây mặt đứng, bụi, cây trong nhà | `PLANT-CLUMP-PLAN-5285x4720`, `PLANT-INDOOR-RUBBER-950x765`, `PLANT-PALM-ELEV-1930x5110` |
| `SANI` | 10 | Thiết bị vệ sinh: bồn cầu, lavabo, bồn tắm, vòi | `SANI-BATHTUB-1525x915`, `SANI-FAUCET-BATH-FRONT-255x115`, `SANI-FAUCET-BATH-SIDE-150x115` |
| `SYMB` | 10 | Ký hiệu bản vẽ: hướng bắc, cao độ, mặt cắt, tiêu đề, thước tỉ lệ | `SYMB-ARROWS-32x19`, `SYMB-CALLOUT-BUBBLE-15x18`, `SYMB-DETAIL-GRID-10x10` |
| `SITE` | 9 | Ngoại thất: hồ bơi, ghế băng, đèn, xe, bàn ghế ngoài trời, đá lát | `SITE-BENCH-ELEV-495x800`, `SITE-CAR-SEDAN-SIDE-4420x1255`, `SITE-HOT-TUB-1755x1755` |
| `DOOR` | 8 | Cửa đi: mặt bằng (có cung mở) và mặt đứng; có bản động | `DOOR-BIFOLD-1525x420`, `DOOR-DYN-ELEV-800x2030`, `DOOR-DYN-PLAN-750x850` |
| `STRUC` | 7 | Ký hiệu và tiết diện kết cấu thép: dầm WF, I, chữ C, mối nối | `STRUC-CHANNEL-110x400`, `STRUC-ELEVATION-SYMBOL-4x4`, `STRUC-I-BEAM-55x100` |
| `WNDW` | 5 | Cửa sổ: mặt bằng và mặt đứng | `WNDW-ALUMINUM-DYN-ELEV-900x900`, `WNDW-DYN-PLAN-900x100`, `WNDW-HALFCIRCLE-ELEV-915x455` |
| `ARCH` | 3 | Cấu kiện kiến trúc: cầu thang xoắn, ống khói, thanh stud | `ARCH-CHIMNEY-ELEV-1180x3100`, `ARCH-STAIR-SPIRAL-1525x1525`, `ARCH-STUD-DYN-38x90` |
| `CIVIL` | 2 | Hạ tầng: ô đỗ xe, hố ga | `CIVIL-MANHOLE-600x600`, `CIVIL-PARKING-STALL-2700x5500` |
| `ELEC` | 1 | Chiếu sáng: đèn huỳnh quang âm trần | `ELEC-LIGHT-RECESSED-DYN-1000x500` |

Quy ước tên và yêu cầu khi tự thêm block nằm ở `blocks/README.md`.

## Kho riêng (`stores` trong kết quả `block list`)

Ngoài 105 tệp ở thư mục gốc, người dùng có thể có thêm các **kho**: thư mục con của thư viện có tệp `index.json`. Kho là bộ block nhập từ bên ngoài (hiện có `dwgshare`, nhập từ các gói nội thất của DWGshare.com). `block list` không in hết kho (có hàng nghìn tệp); nó chỉ có trường `stores`: tên kho, số tệp, số tệp theo loại.

Cách tra:

1. Gọi `block` `list` không tham số, đọc `stores` để biết có kho nào và loại nào (`SOFA`, `TABLE`, `OFFICE`, `DECOR`, `KBB`, `GYM`, `STAIR`, `LAND`, `BRAND` với kho `dwgshare`). Không có `stores` thì máy này chưa có kho riêng: báo người dùng, đừng bịa tên.
2. Lọc một kho: `block` `list` với `data={"kho": "dwgshare", "category": "SOFA", "min_width": 1800, "max_width": 2400, "min_depth": 800, "max_depth": 1000, "limit": 20}` (mọi trường trừ `kho` là tùy chọn, đơn vị mm). Kết quả nằm ở `store.entries`; mỗi mục có `name`, `size_mm`, `bbox_mm`, `category`, `scale_factor` giống trường `library`. `store.matching` là số mục khớp, `shown` là số đã in (tối đa `limit`, mặc định 40). Lọc hẹp rồi mới đọc; đừng xin cả kho.
3. Chèn đúng như block thường (`block` `insert`, `scale` 1): tên trong kho là tên tệp bỏ đuôi, ví dụ `DS-SOFA-0063-2135x865`. Tính điểm chèn bằng `bbox_mm` như ở bước 3 của quy trình.

Điều cần biết về kho `dwgshare`:

- Kho có 1.906 tệp. 1.301 tệp giữ điểm chèn gốc của gói; 605 tệp (`rebased` trong `index.json`) có hình nằm xa điểm chèn gốc nên đã **dời điểm chèn về giữa mép dưới của hình**: `bbox_mm` của chúng là `[-rộng/2, 0, rộng/2, sâu]`, tức gốc (0,0) ở giữa mép dưới. Với tệp không dời, vẫn đọc `bbox_mm` như thường lệ để tính điểm chèn. 20 khối quá nặng nên không nhập được; gói `BRAND` có 15 tệp.
- Các tệp chỉ có tên dạng `DS-<LOẠI>-<số khối>-<rộng>x<sâu>`: nguồn đặt tên khối là `DWGshare.com_<số>`, không nói đó là vật gì. Cái duy nhất biết chắc là **loại gói** (sofa, bàn, văn phòng...) và **kích thước thật** (mm). `meaning` ghi đúng như vậy và `view` là `unverified`.
- Vì thế **sau khi chèn phải kiểm bằng mắt**: gọi `drawing` `get_screenshot` (hoặc phóng to vùng vừa chèn) và xem hình có đúng vật cần không, có nhìn từ trên xuống không. Sai thì xóa đối tượng vừa chèn (`entity` `get` lấy handle rồi xóa), thử mục khác cùng cỡ, và nói rõ với người dùng.
- Loại gói chỉ là gợi ý về chủ đề. Gói `SOFA` ("Most popular sofa sets") phần lớn là cả cụm bố trí phòng khách (sofa kèm bàn, ghế), không phải một chiếc sofa riêng. Có tệp là hình nhìn ngang (mặt đứng): ví dụ một xe ô tô nằm trong nhóm `STAIR`. Các nhóm `KBB`, `DECOR`, `GYM` trộn nhiều loại vật. Kích thước chỉ gợi ý. Giường đôi khoảng 1600x2000, bồn cầu khoảng 400x700.
- Layer và màu nét bên trong block của gói chưa được kiểm; chèn xong xem lại layer đối tượng `INSERT`, và nếu hình mang layer lạ vào bản vẽ thì báo người dùng.
- Mọi khối trong gói mang ghi chú bản quyền "© DWGshare.com. All rights reserved. Reproduction or redistribution without permission is not allowed." Kho chỉ nằm trên máy người dùng. Không đưa tệp của kho lên repo, không đóng gói kèm bản cài, không gửi đi nơi khác.

Thêm kho mới (gói DWG khác) bằng `lt-adapter/tools/import_block_pack.py` (xem docstring); người dùng thêm thủ công bằng cách tạo thư mục con trong `blocks\` có `index.json` đúng mẫu `blocks\README.md`.

## Lưu ý theo loại

- **Block mặt đứng** (`-ELEV`, `-FRONT`, `-SIDE`): chỉ có ý nghĩa trong bản vẽ mặt đứng hoặc mặt cắt; đừng chèn vào mặt bằng.
- **Block động** (tên có `-DYN`): chứa nhiều trạng thái (ví dụ cửa nhiều kích thước, nhiều loại cây). Khung bao trong danh mục là hợp của mọi trạng thái nên lớn hơn hình thực. MCP hiện chưa có công cụ đổi trạng thái hay tham số của block động, nên chỉ chèn được trạng thái mặc định. Muốn trạng thái khác, ưu tiên block tĩnh cùng loại hoặc nhờ người dùng chỉnh trong AutoCAD.
- **Ký hiệu bản vẽ** (`SYMB-`, và `STRUC-` loại ký hiệu): kích thước theo khổ giấy in (ví dụ mũi tên hướng bắc cao 80 mm trên giấy). Với bản vẽ in tỉ lệ 1:T, đặt `scale` = T để ký hiệu ra đúng cỡ trên giấy.
- **Cây và cảnh quan:** cây mặt bằng là hình tán, kích thước tán nằm trong tên. Chọn cây theo đường kính tán cần thể hiện; nếu không có đúng cỡ, chọn gần nhất và nói rõ, đừng phóng thu tùy ý.
- **Phong cách:** bộ mẫu do Autodesk làm theo kiểu nhà ở Mỹ (bồn cầu, bếp, đồ đạc). Khi hồ sơ yêu cầu chi tiết đúng thiết kế Việt Nam, dùng block làm hình tượng chung và nêu rõ.

## Dựng lại thư viện

Các tệp trong `blocks/` được tách từ bản vẽ mẫu của AutoCAD LT (nội dung của Autodesk). Không đưa chúng lên repo công khai và không đóng gói kèm bản cài (gói bỏ qua `.dwg`). Trên máy đã cài AutoCAD LT và đang mở LT:

```
autocad-beiming-mcp-custom\.venv\Scripts\python.exe lt-adapter\tools\extract_sample_blocks.py --catalog-json catalog.json
autocad-beiming-mcp-custom\.venv\Scripts\python.exe lt-adapter\tools\build_block_catalog.py catalog.json blocks\index.json <skill>\references\catalog.md
```

Công cụ chép bản vẽ mẫu sang thư mục tạm, mở từng tệp trong LT (xong gõ `CLOSEALL` để đóng), tách các block đã chọn trong `lt-adapter/tools/sample_blocks.py` và ghi `blocks/index.json`. Muốn thêm một block từ danh mục vào thư viện: thêm một dòng vào `SELECTED` trong `sample_blocks.py` (tệp, tên block gốc, tên thư viện, loại hình, ý nghĩa) rồi chạy lại; tệp đã có được giữ nguyên.

## Giới hạn

- Loại hình (mặt bằng/mặt đứng/ký hiệu) và ý nghĩa của mỗi block suy ra từ tên và kích thước trong bản vẽ mẫu, chưa kiểm bằng mắt từng block.
- Mới kiểm chèn tĩnh trên bản vẽ mm: tỉ lệ, góc xoay và quy đổi inch sang mm. Đã kiểm layer bên trong mọi block (xem bước 6); chưa kiểm màu từng nét bên trong và chưa kiểm block động đổi trạng thái. `SYMB-DETAIL-GRID` và `SYMB-GRAPHIC-SCALE` chèn chậm (vượt 10 giây, báo timeout dù đối tượng vẫn được tạo): sau khi chèn hai block này phải đếm lại bằng `entity` `count` trước khi chèn lại.
- Chèn theo tên tệp chỉ chạy trên backend AutoCAD LT của dự án.
