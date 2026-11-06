AutoCAD MCP Launcher v0.3.4

# Tiếng Việt

Khóa nhóm để gửi đề xuất tri thức nay **được tích hợp sẵn trong launcher** và **ẩn khỏi giao diện**: máy mới cài xong là agent gửi được, không phải nhập khóa.

Đổi:

- Khóa được đưa vào gói phát hành ở bước dựng (từ bí mật `KNOWLEDGE_TEAM_KEY` của GitHub Actions), **không nằm trong mã nguồn công khai** và không nằm trong lịch sử git. Tệp `launcher/team_key.dat` được mã hóa nhẹ (che, không phải bảo mật).
- Tab Cài đặt không còn ô nhập khóa khi gói đã có khóa; hiện dòng "Khóa nhóm đã được tích hợp sẵn". Bản tự dựng không có khóa vẫn hiện ô nhập.
- Thứ tự dùng khóa: biến môi trường `KNOWLEDGE_TEAM_KEY`, rồi khóa nhập tay trong cài đặt, rồi khóa tích hợp sẵn. Tool `knowledge_propose` không bao giờ trả khóa cho agent.

Cần làm:

- **Thoát hẳn launcher rồi mở lại.**

Giới hạn (quan trọng):

- **Đây là che giấu, không phải bảo mật.** Ai tải gói phát hành công khai đều có thể lấy lại khóa, nên khóa chỉ ngăn người lạ gửi bừa, không ngăn người cố ý. Chốt chặn thật vẫn là người duyệt và hàng chờ riêng tư.
- Khóa đã từng hiện trong một ảnh chụp màn hình; nên đổi khóa mới (`wrangler secret put TEAM_KEY` và cập nhật bí mật `KNOWLEDGE_TEAM_KEY`). Khi đổi, các bản launcher đã phát hành sẽ không gửi được cho đến khi cập nhật.
- Cổng chưa có hạn mức theo ngày; các giới hạn khác giữ như v0.3.3.

# English

The team key used to submit knowledge proposals is now **built into the launcher** and **hidden from the UI**: a freshly installed machine can submit straight away, with no key to type.

Changed:

- The key is added to the release package at build time (from the GitHub Actions secret `KNOWLEDGE_TEAM_KEY`); it is **not in the public source** or in git history. `launcher/team_key.dat` is lightly encoded (obscured, not secured).
- The Settings tab shows no key field when the package carries a key; it shows "Khóa nhóm đã được tích hợp sẵn". A self-built copy without a key still shows the field.
- Key order: the `KNOWLEDGE_TEAM_KEY` environment variable, then a key typed in settings, then the embedded key. The `knowledge_propose` tool never returns the key to the agent.

To do:

- **Quit the launcher completely and reopen it.**

Limitations (important):

- **This is obscuring, not security.** Anyone who downloads the public release can recover the key, so it only stops strangers submitting by accident, not a determined person. The real safeguard remains the reviewer and the private queue.
- The key has appeared in a screenshot before; rotate it (`wrangler secret put TEAM_KEY`, then update the `KNOWLEDGE_TEAM_KEY` secret). After rotation, already released launchers cannot submit until updated.
- The gateway still has no daily cap; other limitations as in v0.3.3.
