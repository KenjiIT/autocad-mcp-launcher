---
name: knowledge-promote
description: Chuyển một trang tri thức riêng của dự án (ví dụ trong .llmwiki/wiki hoặc nơi lưu tri thức riêng của dự án) thành bản chung đã gỡ thông tin nhạy cảm và đã đối chiếu bản công khai, đưa vào hàng chờ duyệt. Dùng khi người dùng nói 'đưa lên kho chung', 'chuyển thành tri thức chung', 'gỡ tên dự án rồi chia sẻ', 'promote', 'trang này dùng chung được không'.
---

# Chuyển tri thức riêng thành tri thức chung

Trang riêng của dự án có thể chứa thông tin không được chia sẻ. Skill này tách phần **quy tắc dùng lại được** khỏi phần **dữ kiện riêng**, và chỉ đưa phần đầu vào `proposals/` của thư mục tri thức. Kết quả sau duyệt sẽ **công khai** trên repo `KenjiIT/autocad-knowledge`, nên mức thận trọng cao hơn kho nội bộ. Quy ước và bảng gỡ: [references/quy-uoc.md](references/quy-uoc.md). Thư mục tri thức: theo `knowledge-query`.

## Quy trình

1. **Đọc trang nguồn** và đánh dấu từng đoạn:
   - *Chung:* quy tắc, lý do, cách kiểm tra, hành vi công cụ, cách đọc loại bản vẽ.
   - *Riêng:* tên khách hàng và dự án, mã bản vẽ và lô, số liệu thật (kích thước, diện tích, số căn, tọa độ), kết quả đánh giá một bản vẽ cụ thể, tên người, đường dẫn máy.
2. **Đối chiếu bản công khai** (mục cuối quy ước). Phần chung đã có trên bản công khai thì bỏ khỏi đề xuất; chỉ giữ phần còn thiếu.
3. **Lập bảng gỡ** và đưa người dùng xem trước khi ghi: cột trái là đoạn nguồn, cột phải là "giữ nguyên", "viết lại thành ví dụ vô danh", hoặc "bỏ". Trang nói chủ yếu về một dự án cụ thể (trang entity, đánh giá một bản vẽ) thường chỉ rút được vài quy tắc; nói thẳng nếu gần như không có gì chung để chuyển.
4. **Viết bản chung** vào `proposals/<slug>.md` theo đầu trang trong quy ước: `status: draft`, `reviewed_by` trống, `source` không nêu tên dự án. Ví dụ vô danh ("một dự án căn hộ", "dầm dài gần 30 m"). Số liệu chỉ giữ khi cần cho ý, ở dạng khoảng.
5. **Kiểm tra hai lớp:**
   - Chạy lint bằng skill `knowledge-lint`, có `sensitive-terms.local.txt` chứa mã dự án đang làm.
   - Đọc lại bản chung từ đầu, tìm thứ danh sách không bắt được: tên viết tắt, biệt danh dự án, chi tiết đủ để suy ra dự án nào.
6. **Báo người dùng** tệp đã tạo và những gì đã bỏ. Người dùng đã yêu cầu đưa trang lên nên gửi luôn, bằng tool `knowledge_propose` (cách gọi và xử lý lỗi `NO_TEAM_KEY`, `REJECTED_LOCALLY`: xem bước gửi của skill `knowledge-capture`). Không có tool thì người dùng gửi tệp cho người duyệt. Agent không tự sửa `wiki/` hay repo công khai.
7. Không sửa hay xóa trang nguồn trong dự án.

## Giới hạn

- Không đẩy trang nguồn nguyên văn rồi "sửa sau".
- Còn ngờ một chi tiết thì bỏ chi tiết đó.
