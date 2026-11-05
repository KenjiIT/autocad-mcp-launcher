// Gửi một đề xuất thử tới cổng đã triển khai.
//   PowerShell:  $env:TEAM_KEY = "<khóa nhóm>"; node tools/send-proposal.mjs
// Địa chỉ cổng: biến GATEWAY_URL, mặc định https://knowledge-gateway.kenjiit.workers.dev
const url = process.env.GATEWAY_URL ?? "https://knowledge-gateway.kenjiit.workers.dev";
const key = process.env.TEAM_KEY;
if (!key) {
  console.error("Thiếu biến môi trường TEAM_KEY.");
  process.exit(2);
}

const stamp = new Date().toISOString().slice(0, 10);
const content = `---
title: Đề xuất thử cổng
type: howto
topics: [thu-nghiem]
status: draft
source: Kiểm tra cổng nhận đề xuất
updated: ${stamp}
reviewed_by:
---
# Đề xuất thử

Trang này do script kiểm tra tạo ra để thử cổng. Người duyệt có thể xóa.
`;

const response = await fetch(`${url}/propose`, {
  method: "POST",
  headers: { "x-team-key": key, "content-type": "application/json" },
  body: JSON.stringify({ slug: "thu-cong", content, sender: "send-test" }),
});
console.log(response.status, await response.text());
