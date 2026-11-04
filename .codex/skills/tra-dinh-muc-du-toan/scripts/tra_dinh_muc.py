"""Tra cứu trong PDF định mức / đơn giá xây dựng (bản có lớp chữ).

Dùng:
    py -3 -I tra_dinh_muc.py search  <pdf> <từ khóa ...> [--top 8]
    py -3 -I tra_dinh_muc.py code    <pdf> AF.11200
    py -3 -I tra_dinh_muc.py page    <pdf> <số trang> [--to <trang cuối>]
    py -3 -I tra_dinh_muc.py image   <pdf> <số trang> <file.png> [--dpi 110]
    py -3 -I tra_dinh_muc.py info    <pdf>

Số trang là số thứ tự trang trong PDF (bắt đầu từ 1), không phải số in ở chân trang.
Bản quét (không có chữ) thì `info` báo 0 trang có chữ; khi đó dùng `image` để xem ảnh.
Văn bản trích ra mỗi ô một dòng; bảng nhiều cột bị tách rời, nên đọc số xong phải
đối chiếu bằng `image` trước khi dùng vào dự toán.
Bộ nhớ đệm đặt ở thư mục tạm, khóa theo đường dẫn + kích thước + ngày sửa của PDF.
"""
import argparse
import hashlib
import json
import re
import sys
import tempfile
import unicodedata
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass


def _open(pdf):
    try:
        import pymupdf as fitz
    except ImportError:
        try:
            import fitz
        except ImportError:
            sys.exit("Thiếu PyMuPDF. Cài: py -3 -m pip install pymupdf")
    return fitz.open(pdf)


def norm(text):
    text = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def cache_path(pdf):
    st = Path(pdf).stat()
    key = hashlib.sha1(f"{Path(pdf).resolve()}|{st.st_size}|{int(st.st_mtime)}".encode()).hexdigest()[:16]
    return Path(tempfile.gettempdir()) / f"tra_dinh_muc_{key}.json"


def pages_of(pdf):
    cache = cache_path(pdf)
    if cache.is_file():
        return json.loads(cache.read_text(encoding="utf-8"))
    doc = _open(pdf)
    pages = [" | ".join(s.strip() for s in p.get_text().split("\n") if s.strip()) for p in doc]
    cache.write_text(json.dumps(pages, ensure_ascii=False), encoding="utf-8")
    return pages


def cmd_info(args):
    pages = pages_of(args.pdf)
    with_text = sum(1 for p in pages if len(p) > 80)
    print(f"{len(pages)} trang, {with_text} trang có chữ.")
    if with_text < len(pages) * 0.2:
        print("Có vẻ là bản quét: dùng `image` để xem ảnh, hoặc OCR trước.")


def cmd_search(args):
    pages = pages_of(args.pdf)
    terms = [norm(t) for t in args.terms]
    scored = []
    for i, text in enumerate(pages, 1):
        n = norm(text)
        if all(t in n for t in terms):
            scored.append((sum(n.count(t) for t in terms), i, n))
    scored.sort(key=lambda x: (-x[0], x[1]))
    if not scored:
        print("Không có trang nào chứa đủ mọi từ khóa; thử bớt từ hoặc đổi từ đồng nghĩa.")
        return
    print(f"{len(scored)} trang khớp; hiện {min(args.top, len(scored))} trang đầu theo số lần xuất hiện.")
    for score, i, n in scored[: args.top]:
        raw = pages[i - 1]
        codes = sorted(set(re.findall(r"\b[A-Z]{2}\.\d{3,5}\b", raw)))[:6]
        pos = n.find(terms[0])
        snippet = raw[max(0, pos - 60): pos + 140]
        print(f"- trang {i} (khớp {score}) mã: {', '.join(codes) or '-'}\n    ...{snippet}...")


def cmd_code(args):
    pages = pages_of(args.pdf)
    code = args.code.strip().upper()
    hits = [i for i, t in enumerate(pages, 1) if code in t]
    if not hits:
        print("Không thấy mã này. Mã nhóm dạng AF.11200, mã dòng dạng AF.112 hoặc AF.11211.")
        return
    print(f"Mã {code} xuất hiện ở trang: {', '.join(map(str, hits[:20]))}")
    for i in hits[:2]:
        print(f"\n=== trang {i} ===\n{pages[i - 1]}")


def cmd_page(args):
    pages = pages_of(args.pdf)
    last = args.to or args.page
    for i in range(args.page, min(last, len(pages)) + 1):
        print(f"\n=== trang {i} ===\n{pages[i - 1]}")


def cmd_image(args):
    doc = _open(args.pdf)
    doc[args.page - 1].get_pixmap(dpi=args.dpi).save(args.out)
    print(args.out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("search", "code", "page", "image", "info"):
        p = sub.add_parser(name)
        p.add_argument("pdf")
        if name == "search":
            p.add_argument("terms", nargs="+")
            p.add_argument("--top", type=int, default=8)
        elif name == "code":
            p.add_argument("code")
        elif name == "page":
            p.add_argument("page", type=int)
            p.add_argument("--to", type=int)
        elif name == "image":
            p.add_argument("page", type=int)
            p.add_argument("out")
            p.add_argument("--dpi", type=int, default=110)
    args = ap.parse_args()
    {"search": cmd_search, "code": cmd_code, "page": cmd_page, "image": cmd_image, "info": cmd_info}[args.cmd](args)


if __name__ == "__main__":
    main()
