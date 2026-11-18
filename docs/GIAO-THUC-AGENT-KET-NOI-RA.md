# Giao thức agent kết nối ra server (launcher ↔ server)

Trả lời `de-xuat-launcher-agent-ket-noi-ra.md` của phiên cad-web. Mô tả **những gì launcher thực sự làm** (đã chạy và kiểm), chỗ nào khác đề xuất ban đầu, và chỗ chưa kiểm. Áp dụng cho launcher có tệp `launcher/remote_agent.py` (chưa phát hành; bản kế tiếp sau v0.4.5).

## 1. Mô hình

Launcher là **client đi ra**: mở một kết nối WebSocket tới server, giữ nó, và chuyển các lời gọi HTTP mà server gửi xuống vào gateway nội bộ `http://127.0.0.1:8764`. Không mở cổng nào ở máy local; gateway vẫn chỉ nghe `127.0.0.1`. Tắt mặc định; không cấu hình hoặc đang tắt thì gateway chạy y như cũ.

Vòng lặp chạy **trong tiến trình gateway** (tác vụ nền trong `lifespan`), nên chỉ chạy khi gateway chạy (người dùng đã **Bật kết nối cho agent**, hoặc bật "Tự bật MCP khi mở launcher").

## 2. Kết nối và xác thực

- Địa chỉ phải là `wss://`. `ws://` chỉ chấp nhận khi tên máy là `localhost`, `127.0.0.1` hoặc `::1` **và** biến môi trường `AUTOCAD_MCP_REMOTE_ALLOW_WS=1` (dùng để thử).
- Bắt tay gửi `Authorization: Bearer <token của máy>`. Mã máy (`machine_id`) đi trong khung `hello`, không đi trong header.
- **Từ chối xác thực thì dừng, không nối lại vô hạn:** HTTP `401`/`403` lúc bắt tay, hoặc server đóng kết nối với mã `1008`, `4401`, `4403`. Launcher báo `auth_error` trên app và trong `/status`, và chỉ thử lại khi người dùng đổi cấu hình (ví dụ token mới).
- Lỗi khác (mất mạng, server khởi động lại…) nối lại có lùi dần: 1, 2, 4, 8, 15, 30, rồi 60 giây (±25%). Nối được thì đếm lại từ đầu.
- Giữ kết nối bằng ping/pong của WebSocket, 20 giây một lần, chạy tách khỏi các lời gọi đang xử lý.
- Đổi cấu hình (tắt, đổi địa chỉ, đổi token, đổi danh sách tool bị chặn) thì launcher đóng kết nối hiện tại và nối lại theo cấu hình mới trong vài giây.

## 3. Khung (văn bản JSON, một khung một thông điệp WebSocket)

| Hướng | Khung |
|---|---|
| agent → server (đầu tiên) | `{"type":"hello","machine_id","launcher_version","active","mode","servers"}`. `active` là MCP AutoCAD đang chạy (`"beiming"`, `"puran"` hoặc `null`), `mode` là `"autocad"` hoặc `"ezdxf"`, `servers` là các MCP có trên máy (`["puran","beiming","dutoan"]`) |
| server → agent | `{"type":"request","id","method","path","headers","body_b64"}` |
| agent → server | `{"type":"response_start","id","status","headers"}`, rồi 0 hoặc nhiều `{"type":"response_chunk","id","data_b64"}`, rồi `{"type":"response_end","id"}` |
| agent → server (lỗi) | `{"type":"error","id","code","message"}` |
| server → agent | `{"type":"cancel","id"}` |

Giới hạn:

- `id` là chuỗi không rỗng, tối đa 80 ký tự, không trùng với yêu cầu đang xử lý (trùng thì `DUPLICATE_ID`).
- Một khung WebSocket tối đa **16 MB**; vượt thì thư viện đóng kết nối (mã 1009) và launcher nối lại.
- Thân yêu cầu (sau khi giải base64) tối đa **4 MB**; vượt thì lỗi `TOO_LARGE`, kết nối vẫn giữ.
- Tối đa **4 lời gọi chạy song song**; lời thứ 5 nhận lỗi `BUSY` (server nên xếp hàng phía mình).
- Phản hồi được cắt thành `response_chunk` tối đa **192 KB** thân mỗi khung.
- Chỉ nhận khung văn bản; khung nhị phân bị bỏ qua.

## 4. Chỉ chuyển những gì cần thiết

- **Đường dẫn** phải khớp đúng `/beiming/mcp`, `/puran/mcp` hoặc `/dutoan/mcp` (không có thêm đường dẫn con hay chuỗi truy vấn). Method chỉ `GET`, `POST`, `DELETE`. Mọi đường khác (`/status`, `/puran/select`, `/dutoan/stop`…) bị từ chối ngay, không chạm tới gateway.
- **Header yêu cầu** chuyển xuống gateway: `content-type`, `accept`, `mcp-session-id`, `mcp-protocol-version`, `last-event-id`. Mọi header khác (gồm `authorization`, `cookie`) bị bỏ.
- **Header phản hồi** trả về server: `content-type`, `mcp-session-id`, `cache-control`. Server **phải chuyển tiếp `mcp-session-id` hai chiều** (SDK MCP chuẩn tự làm khi bạn giữ nguyên header), vì gateway dùng mã đó để biết phiên nào đã đọc skill (mục 6).
- **Phản hồi không phải luồng thật:** gateway nhận trọn thân từ MCP con rồi mới trả (kể cả `text/event-stream`), nên `response_start` chỉ được gửi sau khi lời gọi xong. `GET /…/mcp` trả `405` (gateway không có luồng sự kiện độc lập). Một lệnh CAD dài có thể mất tới 960 giây; server nên đặt hạn chờ ≥ 1000 giây cho lời gọi, và không coi im lặng là lỗi.

## 5. Mã lỗi (`error.code`)

| Mã | Nghĩa |
|---|---|
| `FORBIDDEN_PATH` | đường dẫn ngoài danh sách cho phép |
| `METHOD_NOT_ALLOWED` | method ngoài GET, POST, DELETE |
| `BAD_REQUEST` | `body_b64` không phải base64 hợp lệ |
| `TOO_LARGE` | thân yêu cầu quá 4 MB |
| `TOOL_BLOCKED` | lô JSON-RPC có chứa tool bị chặn (xem mục 7) |
| `BUSY` | đang xử lý đủ 4 lời gọi |
| `DUPLICATE_ID` | `id` đang được xử lý |
| `LOCAL_UNAVAILABLE` | gateway nội bộ không phản hồi |
| `LOCAL_TIMEOUT` | gateway nội bộ không trả lời kịp |
| `LOCAL_ERROR` | lỗi khác khi gọi gateway nội bộ |

## 6. `cancel` là "bỏ kết quả" (khác đề xuất ban đầu)

Launcher **không thể dừng một lệnh AutoCAD đang chạy**: lệnh chạy tới hết rồi mới nhả hàng đợi của gateway (đúng để không chạy chồng lên nhau). `cancel` nghĩa là: **không gửi kết quả của lời gọi đó về server**. Không có khung nào cho `id` đã hủy (không `response_*`, không `error`). Lời gọi chưa bắt đầu chạy thì bị bỏ hẳn. Lệnh có tác dụng phụ trên bản vẽ vẫn xảy ra, nên server không nên hủy rồi tự suy ra bản vẽ chưa đổi.

## 7. Tool bị chặn với kết nối từ xa

Chỉ lọc đường dẫn thì người giữ token vẫn gọi được mọi tool trên `/…/mcp`. Mặc định launcher chặn **`launcher_set_backend`** (đổi backend của cả máy sang DXF). Danh sách cấu hình được trong `launcher/state/settings.json`, khóa `remote_blocked_tools` (mảng tên tool hoặc chuỗi ngăn cách bằng dấu phẩy; mảng rỗng là không chặn gì).

- Một `tools/call` bị chặn nhận phản hồi `200` bình thường với kết quả JSON-RPC `isError: true` và nội dung `{"ok":false,"code":"TOOL_BLOCKED","error":"…"}`, để mô hình hiểu được. Lời gọi **không** được chuyển xuống gateway.
- Lô JSON-RPC (mảng) chứa tool bị chặn bị từ chối cả lô bằng khung `error` mã `TOOL_BLOCKED`.

## 8. Cổng chặn skill vẫn áp dụng

Gateway từ chối tool CAD (`SKILL_NOT_READ`) cho tới khi **phiên MCP đó** đã gọi `skills` với `operation=get`, `name=autocad-agent-coordinator`. Phiên được nhận biết bằng `mcp-session-id` mà gateway phát lúc `initialize`. Mỗi phiên MCP phía server (mỗi người dùng web) phải tự đọc skill một lần; mô hình thường làm đúng khi gặp lỗi vì lời từ chối ghi sẵn bước kế tiếp. `dutoan` không bị chặn.

## 9. Ảnh trực tiếp (R4, cách A)

Khi chế độ agent bật, launcher cho tiến trình Beiming biết phép trả ảnh trực tiếp (`AUTOCAD_MCP_ALLOW_INLINE_IMAGES=true`, giới hạn `AUTOCAD_MCP_MAX_INLINE_IMAGE_BYTES`, mặc định **2 MB**, chỉnh bằng `remote_inline_image_max_bytes` trong `settings.json`, trần 8 MB). Tắt chế độ agent thì không đặt gì và mọi thứ như cũ.

- Dùng: gọi tool `view`, `operation="get_screenshot"`, `data={"include_image": true}`. Kết quả có thêm khối `{"type":"image","data":"<base64>","mimeType":"image/png"}` (ngoài văn bản có `payload.screenshot.path`). Ảnh lớn hơn giới hạn thì chỉ có văn bản và đường dẫn.
- **Không phủ:** `drawing` `render_preview` chỉ trả đường dẫn (không có tùy chọn inline). Nếu cần, cách B (gateway tự đọc tệp và gắn ảnh khi có header `X-Inline-Images`) là việc sau.
- Agent local không đổi hành vi: ảnh chỉ kèm theo khi lời gọi xin `include_image`.
- Áp dụng khi tiến trình Beiming được khởi động lại (gateway khởi động lại, hoặc đổi qua lại giữa Beiming và Puran); bật chế độ agent lúc Beiming đang chạy thì chưa có hiệu lực ngay.

## 10. Cấu hình phía launcher

`launcher/state/settings.json` (không commit), nhập ở tab **Cài đặt**, mục "Kết nối ra server (agent từ xa)":

| Khóa | Ý nghĩa |
|---|---|
| `remote_agent_enabled` | bật/tắt (mặc định tắt) |
| `remote_server_url` | địa chỉ `wss://…` |
| `remote_machine_id` | mã máy, gửi trong `hello` |
| `remote_machine_token` | token của máy; ô nhập ẩn, **không hiện lại** sau khi lưu; ghi vào tệp thì launcher giới hạn quyền đọc tệp cho chủ tài khoản (icacls, cố gắng) |
| `remote_blocked_tools` | tool bị chặn (mặc định `["launcher_set_backend"]`) |
| `remote_inline_image_max_bytes` | giới hạn ảnh trực tiếp |

Token không bao giờ vào log (`launcher/logs/remote_agent.log` chỉ ghi tên máy chủ, mã yêu cầu, đường dẫn, mã trạng thái) và không có trong `/status`. Bật lần đầu thì launcher tự cài thư viện `websockets` vào môi trường của gateway (cần mạng).

`/status` của gateway có thêm `remote_agent`: `{"status","detail","since","machine_id","host"}` với `status` là một trong `off`, `connecting`, `connected`, `retrying`, `auth_error`, `config_error`, `missing_lib`, `error`.

## 11. Trả lời năm câu của mục 5

1. `board.forward` **không** phát luồng: nó đọc trọn thân rồi trả (xem mục 4).
2. Ảnh: `view get_screenshot` ghi PNG vào `autocad-beiming-mcp-custom\output\previews\mcp-captures\` và Beiming **đã** có đường trả ảnh trực tiếp; launcher chỉ bật nó (mục 9). `render_preview` chỉ trả đường dẫn.
3. Thư viện: chưa có `websockets` trong venv nào; launcher cài `websockets>=13` vào venv của gateway khi bật chế độ agent.
4. Vòng lặp nằm trong tiến trình gateway.
5. Khác đề xuất: ý nghĩa của `cancel` (mục 6), danh sách tool bị chặn (mục 7), khung `hello` có thêm `servers` đúng thực tế, phải relay `mcp-session-id` (mục 4), cổng chặn skill (mục 8), mã lỗi (mục 5).

## 12. Đã kiểm và chưa kiểm

**Đã kiểm:**
- 39 test tự động với server WebSocket giả và gateway nội bộ giả: sai token dừng nối lại; đóng bằng mã xác thực dừng nối lại; mất kết nối nối lại và gọi tiếp được; chuyển đủ `initialize`, `tools/list`, `tools/call` với đúng header; phản hồi nhiều khối đúng thứ tự; `cancel`; đường dẫn và method ngoài danh sách; thân quá lớn; khung quá lớn; `BUSY`; tool bị chặn; chế độ tắt không nối.
- Một lượt chạy toàn tuyến trên gateway thật (cổng thử) với tiến trình `dutoan` thật: `initialize`, `tools/list` (đủ 12 tool), `tools/call`; cổng chặn skill qua kênh này (`SKILL_NOT_READ`, rồi đọc skill thành công); `mcp-session-id` về tới server; đường dẫn và tool bị chặn; thu hồi token thì dừng nối lại; log không chứa token.
- Giao diện cài đặt (cửa sổ thật, cài đặt giả lập): kiểm tra đầu vào, token không hiện lại.

**Chưa kiểm:**
- Kết nối tới server `wss://` thật (mới thử `ws://` localhost), và chứng chỉ TLS thật.
- Lệnh CAD thật (AutoCAD) đi qua kênh này; ảnh `get_screenshot` inline thật qua kênh này.
- Hành vi lâu dài (nhiều giờ, mạng chập chờn), và nhiều lời gọi CAD song song.
- Nút lưu cấu hình và việc tự cài `websockets` trong cửa sổ launcher thật trên máy khác; giới hạn quyền tệp bằng `icacls` trên máy có chính sách phân quyền khác.
