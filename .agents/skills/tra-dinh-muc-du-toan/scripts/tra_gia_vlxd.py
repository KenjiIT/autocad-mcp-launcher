"""Tra giá vật liệu trong thư mục công bố giá VLXD (các file Excel .xlsx/.xls của doanh nghiệp).

Dùng:
    py -3 tra_gia_vlxd.py search <thư-mục> <từ khóa ...> [--top 15] [--group "2. XI MĂNG"]
    py -3 tra_gia_vlxd.py rows   <thư-mục> "<đường dẫn file tương đối>" [--sheet TÊN] [--from 1] [--to 15]
    py -3 tra_gia_vlxd.py files  <thư-mục>

- `search`: mọi từ khóa phải có trong cùng một dòng (không phân biệt hoa thường, dấu).
  Kết quả ghi nhóm vật liệu, file, sheet, số dòng và nội dung dòng. Cùng một dòng xuất hiện
  ở nhiều file (mẫu VII.2, mẫu VIII, file 737) chỉ hiện một lần.
- `--niem-yet`: chỉ lấy các sheet là "Bảng niêm yết giá"; đây là giá dùng cho đơn giá.
- `rows`: in các dòng của một sheet để xem tiêu đề cột (đơn vị, khu vực, chưa/có VAT).
Cần: py -3 -m pip install openpyxl xlrd   (dùng không có -I vì gói cài ở thư mục người dùng).
Bộ nhớ đệm đặt ở thư mục tạm, khóa theo danh sách file + kích thước + ngày sửa.
Chỉ đọc Excel; PDF quét (ví dụ thép) phải xem ảnh.
"""
import argparse
import hashlib
import json
import os
import sys
import tempfile
import unicodedata
import warnings

warnings.filterwarnings("ignore")
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass


def norm(text):
    text = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def cell(v):
    if v is None:
        return ""
    if isinstance(v, float):
        v = int(v) if v == int(v) else round(v, 4)
    return str(v).strip().replace("\n", " ")


def excel_files(root):
    out = []
    for dp, _, fs in os.walk(root):
        for f in fs:
            if f.lower().endswith((".xlsx", ".xls")) and not f.startswith("~$"):
                out.append(os.path.join(dp, f))
    return sorted(out)


def read_rows(path):
    if path.lower().endswith(".xlsx"):
        import openpyxl
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
        for ws in wb.worksheets:
            for n, row in enumerate(ws.iter_rows(values_only=True), 1):
                c = [cell(v) for v in row]
                if any(c):
                    yield ws.title, n, " | ".join(c).rstrip(" |")
    else:
        import xlrd
        wb = xlrd.open_workbook(path)
        for ws in wb.sheets():
            for r in range(ws.nrows):
                c = [cell(v) for v in ws.row_values(r)]
                if any(c):
                    yield ws.name, r + 1, " | ".join(c).rstrip(" |")


def index(root):
    files = excel_files(root)
    sig = "|".join(f"{os.path.relpath(f, root)}:{os.path.getsize(f)}:{int(os.path.getmtime(f))}" for f in files)
    cache = os.path.join(tempfile.gettempdir(), "tra_gia_vlxd_" + hashlib.sha1(sig.encode()).hexdigest()[:16] + ".json")
    if os.path.isfile(cache):
        return json.load(open(cache, encoding="utf-8"))
    rows, errors = [], []
    for f in files:
        rel = os.path.relpath(f, root)
        try:
            for sheet, n, text in read_rows(f):
                rows.append([rel, sheet, n, text])
        except Exception as e:
            errors.append(f"{rel}: {str(e)[:80]}")
    data = {"rows": rows, "errors": errors}
    json.dump(data, open(cache, "w", encoding="utf-8"), ensure_ascii=False)
    return data


def niem_yet_sheets(rows):
    """Sheet có tiêu đề 'BẢNG NIÊM YẾT GIÁ' hoặc 'Mẫu số 01 Phụ lục VIII' trong 15 dòng đầu."""
    found = set()
    for rel, sheet, n, text in rows:
        if n <= 15:
            t = norm(text)
            if "bang niem yet gia" in t or "mau so 01 phu luc viii" in t:
                found.add((rel, sheet))
    return found


def cmd_search(a):
    data = index(a.root)
    allowed = niem_yet_sheets(data["rows"]) if a.niem_yet else None
    terms = [norm(t) for t in a.terms]
    group = norm(a.group) if a.group else None
    seen, hits = set(), []
    for rel, sheet, n, text in data["rows"]:
        if group and group not in norm(rel):
            continue
        if allowed is not None and (rel, sheet) not in allowed:
            continue
        t = norm(text)
        if all(x in t for x in terms):
            key = norm(text)[:300]
            if key in seen:
                continue
            seen.add(key)
            hits.append((rel, sheet, n, text))
    print(f"{len(hits)} dòng khớp (đã bỏ dòng trùng); hiện {min(a.top, len(hits))} dòng đầu.")
    for rel, sheet, n, text in hits[: a.top]:
        print(f"- [{rel}] sheet '{sheet}' dòng {n}\n    {text[:420]}")
    if data["errors"]:
        print("\nFile không đọc được:", *data["errors"], sep="\n  ")


def cmd_rows(a):
    data = index(a.root)
    want = a.file.replace("/", os.sep)
    got = [r for r in data["rows"] if r[0] == want and (not a.sheet or r[1] == a.sheet) and a.start <= r[2] <= a.to]
    if not got:
        print("Không có dòng nào; kiểm tra đường dẫn (dùng `files`) hoặc tên sheet.")
    for rel, sheet, n, text in got:
        print(f"[{sheet}] {n}: {text[:600]}")


def cmd_files(a):
    data = index(a.root)
    count = {}
    for rel, sheet, n, text in data["rows"]:
        count[rel] = count.get(rel, 0) + 1
    for rel in sorted(count):
        print(f"{count[rel]:6d}  {rel}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("root")
    s.add_argument("terms", nargs="+")
    s.add_argument("--top", type=int, default=15)
    s.add_argument("--group")
    s.add_argument("--niem-yet", action="store_true",
                   help="chỉ lấy sheet là Bảng niêm yết giá (Mẫu 01 Phụ lục VIII); dùng khi lập đơn giá")
    r = sub.add_parser("rows")
    r.add_argument("root")
    r.add_argument("file")
    r.add_argument("--sheet")
    r.add_argument("--from", dest="start", type=int, default=1)
    r.add_argument("--to", type=int, default=15)
    f = sub.add_parser("files")
    f.add_argument("root")
    a = ap.parse_args()
    {"search": cmd_search, "rows": cmd_rows, "files": cmd_files}[a.cmd](a)


if __name__ == "__main__":
    main()
