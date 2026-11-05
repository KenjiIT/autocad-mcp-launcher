// Cổng nhận đề xuất tri thức chung (Cloudflare Worker).
//
// POST /propose   Header X-Team-Key. Body JSON: { slug, content, sender? }
//   -> kiểm tra khóa nhóm, kích thước, đầu trang, nội dung nhạy cảm, giới hạn mỗi ngày
//   -> ghi proposals/<ngày>-<slug>-<mã>.md vào repo INBOX riêng tư qua GitHub API.
// GET  /health    Trả { ok: true }.
//
// Biến cấu hình (wrangler.toml [vars]): INBOX_REPO ("chủ/repo"), INBOX_BRANCH, MAX_BYTES, DAILY_LIMIT.
// Bí mật (wrangler secret put): TEAM_KEY, GITHUB_TOKEN, SENSITIVE_TERMS (tùy chọn, ngăn cách bằng dấu phẩy).
// KV (tùy chọn) RATE: đếm số đề xuất mỗi ngày. Không gắn KV thì không có giới hạn ngày.

const REQUIRED = ["title", "type", "topics", "status", "source", "updated"];
const TYPES = new Set(["concept", "rule", "howto", "pitfall"]);

// Giữ đồng bộ với PATTERNS trong .claude/skills/knowledge-lint/scripts/lint.py
const PATTERNS = [
  ["email", /[\w.+-]+@[\w-]+\.[\w.-]+/],
  ["đường dẫn máy", /[A-Za-z]:[\\/]+(?:Users|Documents and Settings)[\\/]/i],
  ["số điện thoại", /(?<!\d)(?:\+84|0)\d{9,10}(?!\d)/],
  ["khóa/token", /\b(?:sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|github_pat_\w{20,}|AKIA[0-9A-Z]{16})\b/],
];

function json(status, body) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}

function sameSecret(a, b) {
  const x = new TextEncoder().encode(a ?? "");
  const y = new TextEncoder().encode(b ?? "");
  let diff = x.length ^ y.length;
  for (let i = 0; i < Math.max(x.length, y.length); i++) diff |= (x[i] ?? 0) ^ (y[i] ?? 0);
  return diff === 0;
}

export function parseFrontmatter(text) {
  const m = text.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n/);
  if (!m) return null;
  const meta = {};
  for (const line of m[1].split(/\r?\n/)) {
    if (!line.includes(":") || /^[ #]/.test(line)) continue;
    const i = line.indexOf(":");
    meta[line.slice(0, i).trim()] = line.slice(i + 1).split(" #")[0].trim();
  }
  return meta;
}

export function problems(content, env) {
  const found = [];
  const meta = parseFrontmatter(content);
  if (!meta) return ["thiếu đầu trang (frontmatter)"];
  for (const key of REQUIRED) if (!meta[key]) found.push(`thiếu '${key}'`);
  if (meta.type && !TYPES.has(meta.type)) found.push(`type '${meta.type}' không hợp lệ`);
  if (meta.status && meta.status !== "draft") found.push("status phải là draft");
  if (meta.reviewed_by) found.push("reviewed_by phải để trống (người duyệt điền)");
  for (const [label, re] of PATTERNS) if (re.test(content)) found.push(`có vẻ chứa ${label}`);
  const lower = content.toLowerCase();
  for (const term of (env.SENSITIVE_TERMS ?? "").split(",").map((t) => t.trim()).filter(Boolean)) {
    if (lower.includes(term.toLowerCase())) found.push("chứa thuật ngữ nhạy cảm của công ty");
  }
  return found;
}

function toBase64(text) {
  const bytes = new TextEncoder().encode(text);
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin);
}

async function underDailyLimit(env) {
  if (!env.RATE) return true;
  const limit = Number(env.DAILY_LIMIT ?? 50);
  const key = `day:${new Date().toISOString().slice(0, 10)}`;
  const used = Number((await env.RATE.get(key)) ?? 0);
  if (used >= limit) return false;
  await env.RATE.put(key, String(used + 1), { expirationTtl: 172800 });
  return true;
}

async function propose(request, env) {
  if (!sameSecret(request.headers.get("x-team-key"), env.TEAM_KEY)) return json(401, { ok: false, error: "Sai khóa nhóm." });

  const maxBytes = Number(env.MAX_BYTES ?? 51200);
  const raw = await request.text();
  if (new TextEncoder().encode(raw).length > maxBytes + 2048) return json(413, { ok: false, error: "Đề xuất quá lớn." });

  let body;
  try {
    body = JSON.parse(raw);
  } catch {
    return json(400, { ok: false, error: "Body không phải JSON." });
  }
  const { slug, content } = body ?? {};
  const sender = String(body?.sender ?? "").replace(/[^\w .-]/g, "").slice(0, 60);
  if (typeof slug !== "string" || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug) || slug.length > 80)
    return json(400, { ok: false, error: "slug phải là chữ thường không dấu, nối bằng gạch ngang, tối đa 80 ký tự." });
  if (typeof content !== "string" || !content.trim()) return json(400, { ok: false, error: "Thiếu content." });
  if (new TextEncoder().encode(content).length > maxBytes) return json(413, { ok: false, error: "Đề xuất quá lớn." });

  const issues = problems(content, env);
  if (issues.length) return json(422, { ok: false, error: "Đề xuất chưa đạt.", issues });

  if (!(await underDailyLimit(env))) return json(429, { ok: false, error: "Hôm nay đã nhận đủ số đề xuất. Thử lại ngày mai." });

  const id = crypto.randomUUID().slice(0, 8);
  const path = `proposals/${new Date().toISOString().slice(0, 10)}-${slug}-${id}.md`;
  const note = sender ? `\n\nGửi bởi: ${sender}` : "";
  const response = await fetch(`https://api.github.com/repos/${env.INBOX_REPO}/contents/${path}`, {
    method: "PUT",
    headers: {
      authorization: `Bearer ${env.GITHUB_TOKEN}`,
      accept: "application/vnd.github+json",
      "user-agent": "knowledge-gateway",
      "content-type": "application/json",
    },
    body: JSON.stringify({
      message: `proposal: ${slug}${note}`,
      content: toBase64(content),
      branch: env.INBOX_BRANCH ?? "main",
    }),
  });
  if (!response.ok) return json(502, { ok: false, error: `GitHub trả ${response.status}.` });
  return json(201, { ok: true, id, path });
}

export default {
  async fetch(request, env) {
    const { pathname } = new URL(request.url);
    if (pathname === "/health" && request.method === "GET") return json(200, { ok: true });
    if (pathname === "/propose" && request.method === "POST") return propose(request, env);
    return json(404, { ok: false, error: "Không có đường dẫn này." });
  },
};
