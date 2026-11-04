"""Tra đơn giá trong bảng giá nội bộ trích từ DMS (file gia-mat-hang-DMS-*.xlsx).

DỮ LIỆU NỘI BỘ, KHÔNG CHIA SẺ RA NGOÀI. Script chỉ đọc file ở đường dẫn bạn đưa; không chép
số liệu vào skill, không ghi file ra ngoài thư mục tạm.

Dùng:
    py -3 tra_gia_dms.py search <file.xlsx> <từ khóa ...> [--unit m3] [--exclude "phu phi"] [--top 8]
    py -3 tra_gia_dms.py rows   <file.xlsx> <từ khóa ...> [--unit m3] [--top 20]
    py -3 tra_gia_dms.py info   <file.xlsx>

- `search`: gom theo (tên chuẩn hóa, đơn vị chuẩn hóa), in số mẫu, số nhà cung cấp, số dự án,
  trung vị, thấp nhất/cao nhất SAU KHI loại giá bất thường, giá gần nhất và nguồn của nó.
  Mọi từ khóa phải có trong tên mặt hàng (không phân biệt hoa thường, dấu).
- `rows`: liệt kê từng dòng (dự án, nhà cung cấp, ngày, giá, file/sheet/dòng) để kiểm.
Loại khỏi thống kê: giá dưới 1.000 đồng (lỗi nhập liệu hay hệ số), dòng trùng hoàn toàn.
Dòng khối lượng âm hoặc 0 vẫn tính (giá hợp đồng vẫn có giá trị) nhưng đếm riêng.
Cần pandas-free: chỉ dùng openpyxl (py -3 -m pip install openpyxl), không dùng -I.
"""
import argparse
import hashlib
import json
import os
import re
import statistics
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

MIN_PRICE = 1000
UNIT_MAP = {
    "cai": "cái", "chiec": "cái", "pcs": "cái", "pc": "cái", "pce": "cái", "nr": "cái", "no": "cái",
    "m3": "m3", "m³": "m3", "khoi": "m3",
    "m2": "m2", "m²": "m2",
    "m": "m", "met": "m", "md": "m", "mdai": "m",
    "bo": "bộ", "set": "bộ", "tu": "tủ", "vien": "viên", "kg": "kg", "tan": "tấn", "ton": "tấn",
    "ca": "ca", "lo": "lỗ", "cay": "cây", "bao": "bao", "lit": "lít", "l": "lít",
}


def norm(text):
    text = unicodedata.normalize("NFD", str(text).lower().replace("đ", "d"))
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9.+%/x ]+", " ", text).strip()


def squash(text):
    return re.sub(r"\s+", " ", norm(text))


def unit_of(raw):
    u = re.sub(r"[\s./]", "", norm(raw))
    return UNIT_MAP.get(u, (str(raw) or "").strip().lower() or "?")


def load(path):
    st = os.stat(path)
    key = hashlib.sha1(f"{os.path.abspath(path)}|{st.st_size}|{int(st.st_mtime)}".encode()).hexdigest()[:16]
    cache = os.path.join(tempfile.gettempdir(), f"tra_gia_dms_{key}.json")
    if os.path.isfile(cache):
        return json.load(open(cache, encoding="utf-8"))
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    if "Chi tiết" not in wb.sheetnames:
        sys.exit("Không thấy sheet 'Chi tiết'. Đây có phải file bảng giá DMS không?")
    rows = []
    it = wb["Chi tiết"].iter_rows(values_only=True)
    head = [str(h or "").strip() for h in next(it)]
    col = {h: i for i, h in enumerate(head)}
    need = ["Ngày duyệt cuối", "Dự án", "NCC", "Mặt hàng", "ĐVT", "Khối lượng", "Đơn giá", "Tiêu đề cột đơn giá", "Tên file", "Sheet", "Dòng", "Số HĐ/PLHĐ"]
    missing = [n for n in need if n not in col]
    if missing:
        sys.exit("Thiếu cột: " + ", ".join(missing))
    for r in it:
        g = lambda k: r[col[k]] if r[col[k]] is not None else ""
        try:
            price = float(g("Đơn giá"))
        except (TypeError, ValueError):
            continue
        qty = g("Khối lượng")
        try:
            qty = float(qty)
        except (TypeError, ValueError):
            qty = None
        rows.append([str(g("Ngày duyệt cuối"))[:10], str(g("Dự án")), str(g("NCC")), str(g("Mặt hàng")),
                     str(g("ĐVT")), qty, price, str(g("Tiêu đề cột đơn giá")), str(g("Tên file")),
                     str(g("Sheet")), str(g("Dòng")), str(g("Số HĐ/PLHĐ"))])
    json.dump(rows, open(cache, "w", encoding="utf-8"), ensure_ascii=False)
    return rows


def select(rows, terms, unit, exclude):
    terms = [squash(t) for t in terms]
    ex = [squash(e) for e in exclude or []]
    want = unit_of(unit) if unit else None
    seen, out, dropped_low, dropped_dup = set(), [], 0, 0
    for r in rows:
        name = squash(r[3])
        if not all(t in name for t in terms) or any(e in name for e in ex):
            continue
        if want and unit_of(r[4]) != want:
            continue
        if r[6] < MIN_PRICE:
            dropped_low += 1
            continue
        key = (r[11], name, r[6], r[5], r[2])
        if key in seen:
            dropped_dup += 1
            continue
        seen.add(key)
        out.append(r)
    return out, dropped_low, dropped_dup


def fmt(v):
    return f"{v:,.0f}".replace(",", ".")


def cmd_search(a):
    rows = load(a.file)
    sel, low, dup = select(rows, a.terms, a.unit, a.exclude)
    groups = {}
    for r in sel:
        groups.setdefault((squash(r[3]), unit_of(r[4])), []).append(r)
    print(f"{len(sel)} dòng, {len(groups)} nhóm (tên chuẩn hóa, đơn vị). Loại {low} dòng giá < {MIN_PRICE} đồng và {dup} dòng trùng.")
    if not groups:
        print("Không có kết quả; thử bớt từ khóa hoặc bỏ --unit.")
        return
    ranked = sorted(groups.items(), key=lambda kv: -len(kv[1]))[: a.top]
    for (name, unit), g in ranked:
        prices = [r[6] for r in g]
        latest = max(g, key=lambda r: r[0])
        ncc, prj = len({r[2] for r in g}), len({r[1] for r in g})
        warn = "  [ÍT MẪU: dưới 3 dòng hoặc 1 dự án, không coi trung vị là giá thị trường]" if len(g) < 3 or prj < 2 else ""
        print(f"\n- {name}  [{unit}]  mẫu {len(g)}, NCC {ncc}, dự án {prj}{warn}")
        print(f"    trung vị {fmt(statistics.median(prices))} | thấp {fmt(min(prices))} | cao {fmt(max(prices))}")
        print(f"    gần nhất {fmt(latest[6])} ngày {latest[0]} | {latest[2]} | {latest[1]}")
        print(f"    nguồn gần nhất: {latest[8]} / {latest[9]} / dòng {latest[10]} | cột giá: {latest[7]}")
        neg = sum(1 for r in g if r[5] is not None and r[5] < 0)
        zero = sum(1 for r in g if r[5] == 0)
        if neg or zero:
            print(f"    (khối lượng âm {neg}, bằng 0 {zero})")
    print("\nGiá trước VAT hay không phụ thuộc cột giá của từng file; xem 'cột giá' và mở file gốc nếu dùng cho thanh toán.")


def cmd_rows(a):
    rows = load(a.file)
    sel, _, _ = select(rows, a.terms, a.unit, a.exclude)
    sel.sort(key=lambda r: r[0], reverse=True)
    for r in sel[: a.top]:
        print(f"{r[0]} | {fmt(r[6])} / {unit_of(r[4])} | KL {r[5]} | {r[3][:70]} | {r[2][:40]} | {r[1][:40]} | {r[8]} / {r[9]} / {r[10]}")
    print(f"({min(a.top, len(sel))}/{len(sel)} dòng, mới nhất trước)")


def cmd_info(a):
    rows = load(a.file)
    dates = sorted(r[0] for r in rows)
    print(f"{len(rows)} dòng giá; ngày duyệt {dates[0]} đến {dates[-1]}; {len({r[1] for r in rows})} dự án; {len({r[2] for r in rows})} NCC.")
    print(f"Giá dưới {MIN_PRICE} đồng: {sum(1 for r in rows if r[6] < MIN_PRICE)} dòng.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("search", "rows", "info"):
        p = sub.add_parser(name)
        p.add_argument("file")
        if name != "info":
            p.add_argument("terms", nargs="+")
            p.add_argument("--unit")
            p.add_argument("--exclude", action="append")
            p.add_argument("--top", type=int, default=8 if name == "search" else 20)
    a = ap.parse_args()
    {"search": cmd_search, "rows": cmd_rows, "info": cmd_info}[a.cmd](a)


if __name__ == "__main__":
    main()
