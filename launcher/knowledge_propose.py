"""Send a proposed knowledge page to the shared-knowledge gateway.

The gateway (see knowledge-gateway/) only writes into a private inbox that a reviewer
reads; nothing here changes the public pages.  Content is checked on this machine first,
so a page with an e-mail address, a machine path, a key or one of the user's own
sensitive terms never leaves the computer.
"""
import json
import os
import re
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SETTINGS_FILE = ROOT / "launcher" / "state" / "settings.json"
DEFAULT_GATEWAY_URL = "https://knowledge-gateway.kenjiit.workers.dev"
MAX_BYTES = 51200
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
REQUIRED = ("title", "type", "topics", "status", "source", "updated")
TYPES = {"concept", "rule", "howto", "pitfall"}
# Keep in step with PATTERNS in knowledge-gateway/src/index.js and
# .claude/skills/knowledge-lint/scripts/lint.py.
PATTERNS = (
    ("email", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")),
    ("đường dẫn máy", re.compile(r"[A-Za-z]:[\\/]+(?:Users|Documents and Settings)[\\/]", re.I)),
    ("số điện thoại", re.compile(r"(?<!\d)(?:\+84|0)\d{9,10}(?!\d)")),
    ("khóa/token", re.compile(r"\b(?:sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|github_pat_\w{20,}|AKIA[0-9A-Z]{16})\b")),
)

TOOL = {
    "name": "knowledge_propose",
    "description": (
        "Gửi một trang tri thức đề xuất lên hàng chờ duyệt của kho tri thức chung. Sau khi người duyệt "
        "chấp nhận, trang trở thành CÔNG KHAI. Chỉ gọi khi người dùng đã xem và đồng ý nội dung, và nội dung đã "
        "gỡ tên khách hàng, mã dự án, số liệu thật, tên người, đường dẫn máy (xem skill knowledge-capture). "
        "content là markdown có đầu trang: title, type (concept|rule|howto|pitfall), topics, status: draft, "
        "source, updated (YYYY-MM-DD), reviewed_by để trống. Launcher kiểm tra nội dung trên máy trước khi gửi."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "slug": {"type": "string", "description": "Tên tệp: chữ thường không dấu nối bằng gạch ngang, ví dụ loi-lt-hai-cua-so."},
            "content": {"type": "string", "description": "Toàn bộ trang markdown, gồm đầu trang."},
            "sender": {"type": "string", "description": "Nhãn người gửi (tùy chọn)."},
        },
        "required": ["slug", "content"],
    },
    "annotations": {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": True},
}


def load_settings():
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def gateway_url(settings=None):
    settings = settings if settings is not None else load_settings()
    value = os.environ.get("KNOWLEDGE_GATEWAY_URL") or settings.get("knowledge_gateway_url") or DEFAULT_GATEWAY_URL
    return str(value).strip().rstrip("/")


def team_key(settings=None):
    settings = settings if settings is not None else load_settings()
    return str(os.environ.get("KNOWLEDGE_TEAM_KEY") or settings.get("knowledge_team_key") or "").strip()


def knowledge_dir(settings=None):
    settings = settings if settings is not None else load_settings()
    saved = settings.get("knowledge_dir")
    return Path(saved) if isinstance(saved, str) and saved else Path.home() / "autocad-knowledge"


def sensitive_terms(folder):
    """One term per line in <knowledge folder>/sensitive-terms.local.txt (never uploaded)."""
    try:
        lines = (Path(folder) / "sensitive-terms.local.txt").read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    return [line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#")]


def front_matter(content):
    match = re.match(r"---\r?\n(.*?)\r?\n---\r?\n", content, re.S)
    if not match:
        return None
    meta = {}
    for line in match.group(1).splitlines():
        if ":" not in line or line.startswith((" ", "#")):
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.split(" #", 1)[0].strip()
    return meta


def problems(content, terms=()):
    """Reasons the page must not be sent; empty when it may go."""
    found = []
    meta = front_matter(content)
    if meta is None:
        found.append("thiếu đầu trang (frontmatter)")
    else:
        found += [f"thiếu '{key}'" for key in REQUIRED if not meta.get(key)]
        if meta.get("type") and meta["type"] not in TYPES:
            found.append(f"type '{meta['type']}' không hợp lệ")
        if meta.get("status") and meta["status"] != "draft":
            found.append("status phải là draft")
        if meta.get("reviewed_by"):
            found.append("reviewed_by phải để trống (người duyệt điền)")
        if meta.get("updated"):
            try:
                date.fromisoformat(meta["updated"])
            except ValueError:
                found.append("updated phải dạng YYYY-MM-DD")
    for label, pattern in PATTERNS:
        if pattern.search(content):
            found.append(f"có vẻ chứa {label}")
    lowered = content.lower()
    for term in terms:
        if term.lower() in lowered:
            found.append("chứa thuật ngữ nhạy cảm trong sensitive-terms.local.txt")
            break
    return found


def post(url, key, payload, timeout=30, opener=urllib.request.urlopen):
    request = urllib.request.Request(
        f"{url}/propose", data=json.dumps(payload).encode("utf-8"), method="POST",
        headers={"content-type": "application/json", "x-team-key": key, "user-agent": "autocad-mcp-launcher"})
    try:
        with opener(request, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read().decode("utf-8"))
        except ValueError:
            return exc.code, {"ok": False, "error": f"Cổng trả {exc.code}."}


def propose(arguments, settings=None, opener=urllib.request.urlopen):
    """Run the knowledge_propose tool; returns (payload, is_error)."""
    settings = settings if settings is not None else load_settings()
    slug, content = arguments.get("slug"), arguments.get("content")
    if not isinstance(slug, str) or len(slug) > 80 or not SLUG.fullmatch(slug):
        return {"ok": False, "error": "slug phải là chữ thường không dấu, nối bằng gạch ngang, tối đa 80 ký tự."}, True
    if not isinstance(content, str) or not content.strip():
        return {"ok": False, "error": "Thiếu content."}, True
    if len(content.encode("utf-8")) > MAX_BYTES:
        return {"ok": False, "error": "Đề xuất quá lớn (tối đa 50 KB)."}, True
    key = team_key(settings)
    if not key:
        return {"ok": False, "code": "NO_TEAM_KEY",
                "error": "Chưa có khóa nhóm. Nhập khóa ở tab Cài đặt của launcher, mục Gửi đề xuất tri thức."}, True
    issues = problems(content, sensitive_terms(knowledge_dir(settings)))
    if issues:
        return {"ok": False, "code": "REJECTED_LOCALLY", "sent": False, "issues": issues,
                "error": "Đề xuất chưa đạt kiểm tra trên máy; chưa gửi gì đi."}, True
    sender = arguments.get("sender") or settings.get("knowledge_sender") or ""
    try:
        status, body = post(gateway_url(settings), key, {"slug": slug, "content": content, "sender": str(sender)},
                            opener=opener)
    except (OSError, ValueError) as exc:
        return {"ok": False, "sent": False, "error": f"Không kết nối được cổng: {exc}"}, True
    if status == 201 and body.get("ok"):
        return {"ok": True, "sent": True, "id": body.get("id"), "path": body.get("path"),
                "note": "Đã vào hàng chờ duyệt. Chưa công khai cho tới khi người duyệt chấp nhận."}, False
    body.setdefault("ok", False)
    body["status"] = status
    return body, True
