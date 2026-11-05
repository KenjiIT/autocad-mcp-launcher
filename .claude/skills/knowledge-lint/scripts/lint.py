"""Kiểm tra thư mục tri thức chung (wiki/ đã duyệt + proposals/ chờ duyệt).

Chạy:  py -3 lint.py --root <thư mục tri thức> [--terms FILE] [--strict]

Thư mục tri thức mặc định: biến COMMON_KNOWLEDGE_DIR, nếu không có thì ~/autocad-knowledge.
Thuật ngữ nhạy cảm riêng (mã dự án, tên khách hàng...): file một dòng một thuật ngữ, mặc định
<root>/sensitive-terms.local.txt (không đưa lên git). Thiếu file thì chỉ quét các mẫu chung.

Lỗi (exit 1): đầu trang sai ở proposals/, thiếu mục lục, liên kết gãy, nội dung nhạy cảm.
Cảnh báo (exit 0, hoặc exit 1 với --strict): trang wiki chưa có đầu trang, trang quá một năm.
"""
import argparse
import os
import re
import sys
from datetime import date
from pathlib import Path

TYPES = {"concept", "rule", "howto", "pitfall"}
STATUSES = {"draft", "confirmed", "outdated"}
REQUIRED = ("title", "type", "topics", "status", "source", "updated")
STALE_DAYS = 365

PATTERNS = {
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "đường dẫn máy": re.compile(r"[A-Za-z]:[\\/]+(?:Users|Documents and Settings)[\\/]", re.I),
    "số điện thoại": re.compile(r"(?<!\d)(?:\+84|0)\d{9,10}(?!\d)"),
    "khóa/token": re.compile(r"\b(?:sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|github_pat_\w{20,}|AKIA[0-9A-Z]{16})\b"),
}


def parse(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"---\r?\n(.*?)\r?\n---\r?\n(.*)", text, re.S)
    if not m:
        return None, text
    meta = {}
    for line in m.group(1).splitlines():
        if ":" not in line or line.startswith((" ", "#")):
            continue
        key, value = line.split(":", 1)
        value = value.split(" #", 1)[0].strip()
        if value.startswith("[") and value.endswith("]"):
            value = [v.strip() for v in value[1:-1].split(",") if v.strip()]
        meta[key.strip()] = value
    return meta, m.group(2)


def check_meta(rel, meta, errors, warnings, proposal):
    for key in REQUIRED:
        if not meta.get(key):
            errors.append(f"{rel}: thiếu '{key}'")
    if meta.get("type") and meta["type"] not in TYPES:
        errors.append(f"{rel}: type '{meta['type']}' không hợp lệ ({', '.join(sorted(TYPES))})")
    if meta.get("status") and meta["status"] not in STATUSES:
        errors.append(f"{rel}: status '{meta['status']}' không hợp lệ")
    if proposal:
        if meta.get("reviewed_by"):
            errors.append(f"{rel}: trang trong proposals/ chưa được có reviewed_by (người duyệt điền khi chuyển sang wiki/)")
        if meta.get("status") not in (None, "draft"):
            errors.append(f"{rel}: trang trong proposals/ phải là draft")
    else:
        if meta.get("status") == "draft":
            errors.append(f"{rel}: trang trong wiki/ không được là draft")
        if not meta.get("reviewed_by"):
            warnings.append(f"{rel}: có đầu trang nhưng thiếu reviewed_by")
    try:
        age = (date.today() - date.fromisoformat(str(meta.get("updated", "")))).days
        if age > STALE_DAYS and not proposal and meta.get("status") != "outdated":
            warnings.append(f"{rel}: {age} ngày chưa cập nhật, xem lại còn đúng không")
    except ValueError:
        errors.append(f"{rel}: updated phải dạng YYYY-MM-DD")


def main():
    default_root = os.environ.get("COMMON_KNOWLEDGE_DIR") or str(Path.home() / "autocad-knowledge")
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=default_root, type=Path)
    ap.add_argument("--terms", type=Path)
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()
    root = args.root

    if not (root / "wiki").is_dir():
        sys.exit(f"Không thấy {root / 'wiki'}. Bấm 'Tải tri thức' trong launcher hoặc truyền --root.")

    terms_file = args.terms or root / "sensitive-terms.local.txt"
    terms = []
    if terms_file.is_file():
        terms = [t.strip() for t in terms_file.read_text(encoding="utf-8").splitlines() if t.strip() and not t.startswith("#")]
    else:
        print(f"LƯU Ý   không có {terms_file.name}: chỉ quét mẫu chung (email, số điện thoại, đường dẫn máy, khóa)")

    pages = sorted(p for p in (root / "wiki").rglob("*.md") if p.name != "index.md")
    proposals = sorted((root / "proposals").glob("*.md")) if (root / "proposals").is_dir() else []
    slugs = {p.stem for p in pages + proposals}
    index_file = root / "wiki" / "index.md"
    index = index_file.read_text(encoding="utf-8") if index_file.is_file() else ""
    errors, warnings = [], []

    if not index_file.is_file():
        errors.append("wiki/index.md: không có mục lục")

    for path in pages + proposals:
        rel = path.relative_to(root).as_posix()
        proposal = path in proposals
        meta, body = parse(path)
        if meta is None:
            (errors if proposal else warnings).append(f"{rel}: thiếu đầu trang (frontmatter)")
        else:
            check_meta(rel, meta, errors, warnings, proposal)
        if not proposal and path.relative_to(root / "wiki").as_posix() not in index:
            errors.append(f"{rel}: chưa có trong wiki/index.md")
        for link in re.findall(r"\[\[([^\]|#]+)", body):
            if link.strip() not in slugs:
                errors.append(f"{rel}: liên kết gãy [[{link.strip()}]]")
        full = path.read_text(encoding="utf-8")
        for term in terms:
            if re.search(re.escape(term), full, re.I):
                errors.append(f"{rel}: chứa thuật ngữ nhạy cảm '{term}'")
        for label, pattern in PATTERNS.items():
            if pattern.search(full):
                errors.append(f"{rel}: có vẻ chứa {label}")

    for e in errors:
        print("LỖI     ", e)
    for w in warnings:
        print("CẢNH BÁO", w)
    print(f"{len(pages)} trang wiki, {len(proposals)} đề xuất, {len(errors)} lỗi, {len(warnings)} cảnh báo")
    sys.exit(1 if errors or (warnings and args.strict) else 0)


if __name__ == "__main__":
    main()
