"""Thêm công tác mới vào file dự toán GXD (xlsm) bằng Excel COM, không cần phần mềm GXD.

    py -3 them_cong_tac_gxd.py spec.json

spec.json:
{
  "file_in":  "đường dẫn xlsm nguồn (không bị sửa)",
  "file_out": "đường dẫn xlsm kết quả",
  "items": [
    {"nhom": "D.",                       # đầu tiêu đề nhóm trong Du toan XD (cột F, dòng E='HM')
     "ma_dm": "AF.32300", "ma_dg": "AF.32300",
     "noi_dung": "Bê tông xà dầm, giằng, sàn mái", "dvt": "m³", "kl": null,   # kl: null = để trống
     "vl":  [{"msvt": "VX.VBT", "ten": "Vữa bê tông", "dvt": "m³", "dm": 1.015, "gia": null}],
     "vl_khac": 1,                      # % vật liệu khác (bỏ nếu không có)
     "nc":  [{"msvt": "NC2", "dm": 1.66}],
     "may": [{"msvt": "MX.BOM50", "ten": "Máy bơm bê tông 50 m³/h", "dvt": "ca", "dm": 0.033, "gia": null}],
     "may_khac": 1}
  ]
}
- Vật tư đã có trong `TH vat tu XD` (khớp MSVT, cột B) thì dùng lại, không đổi giá. Chưa có thì thêm dòng mới;
  `gia` null thì giá = 0 và dòng tô vàng "CHƯA CÓ GIÁ" để người dùng nhập. MSVT mới do bạn tự đặt (tiền tố VX./MX.):
  không phải mã của cơ sở dữ liệu GXD.
- Giữ nguyên thứ tự: thêm vào cuối nhóm; khối phân tích đơn giá thêm vào cuối `Don gia XD`.
- Cuối cùng tự kiểm: tính lại chi phí trực tiếp từ định mức x giá và so với ô công thức; đếm ô lỗi.
Chỉ chạy trên bản sao (file_out). Cần Windows + Excel + pywin32.
"""
import json
import re
import shutil
import sys
from pathlib import Path

import win32com.client as win32

XL_UP = -4162
PASTE_FORMATS = -4122
YELLOW = 65535
BASELINE_ERR = {"Config": 18, "Don gia tong hop": 30, "TH gia du thau": 2, "Ts": 1, "Bia-Dutoan": 1,
                "Bia-DTXD": 1, "Bia-DTTB": 1, "TM": 1, "Tai lieu": 1, "Dich thuat": 1,
                "BC tham dinh": 2, "BC tham tra": 2}


def val(ws, r, c):
    return ws.Cells(r, c).Value2


def last_row(ws, col):
    """Dòng cuối có giá trị của cột (quét giá trị; End(xlUp) từng trả sai trên file này)."""
    n = ws.UsedRange.Row + ws.UsedRange.Rows.Count
    vals = ws.Range(ws.Cells(1, col), ws.Cells(n, col)).Value2
    return max((i for i, row in enumerate(vals, start=1) if row[0] not in (None, "")), default=1)


def num(x):
    return float(x) if isinstance(x, (int, float)) else 0.0


class Book:
    def __init__(self, xl, path):
        self.wb = xl.Workbooks.Open(str(path), 0, False)
        self.dt = self.wb.Worksheets("Du toan XD")
        self.dg = self.wb.Worksheets("Don gia XD")
        self.vt = self.wb.Worksheets("TH vat tu XD")
        self.checks = []

    # ---------- TH vat tu XD ----------
    def vt_sections(self):
        ws, n = self.vt, last_row(self.vt, 3)
        s = {}
        for r in range(7, n + 1):
            a, c = val(ws, r, 1), val(ws, r, 3)
            if a == "A": s["vl_h"] = r
            elif a == "B": s["nc_h"] = r
            elif a == "C": s["m_h"] = r
            elif a == "T": s["tot"] = r
            if c == "Vật liệu khác": s["vl_k"] = r
            if c == "Máy khác": s["m_k"] = r
        return s

    def vt_find(self, msvt):
        s = self.vt_sections()
        for r in range(8, s["tot"]):
            if val(self.vt, r, 2) == msvt:
                return r
        return None

    def vt_ensure(self, kind, it):
        """Trả về số dòng của vật tư trong TH vat tu XD; thêm nếu chưa có."""
        r = self.vt_find(it["msvt"])
        if r:
            return r
        s = self.vt_sections()
        if kind == "vl": p, sec = s["vl_k"], s["vl_h"]
        elif kind == "nc": p, sec = s["m_h"] - 1, s["nc_h"]
        else: p, sec = s["m_k"], s["m_h"]
        ws = self.vt
        nb = p - 1  # dòng vật tư kế bên, dùng làm mẫu công thức và định dạng
        ws.Rows(p).Insert()
        ws.Rows(nb).Copy()
        ws.Rows(p).PasteSpecial(PASTE_FORMATS)
        ws.Application.CutCopyMode = False
        for c in range(1, 17):
            f = ws.Cells(nb, c).Formula
            if isinstance(f, str) and f.startswith("="):
                # đổi tham chiếu ô của chính dòng mẫu sang dòng mới (không đụng hằng số hàng tổng)
                f = re.sub(r"(?<![A-Z$!:\d])([A-Z]{1,2})%d(?!\d)" % nb, lambda m: m.group(1) + str(p), f)
                ws.Cells(p, c).Formula = f
        ws.Cells(p, 1).Value2 = None
        ws.Cells(p, 2).Value2 = it["msvt"]
        ws.Cells(p, 3).Value2 = it.get("ten", it["msvt"])
        ws.Cells(p, 4).Value2 = it.get("dvt", "")
        gia = it.get("gia")
        ws.Cells(p, 6).Value2 = gia if gia is not None else 0
        ws.Cells(p, 7).Value2 = gia if gia is not None else 0
        if gia is None:
            ws.Range(ws.Cells(p, 1), ws.Cells(p, 7)).Interior.Color = YELLOW
            ws.Cells(p, 13).Value2 = "CHƯA CÓ GIÁ - nhập ở cột G"
        return p

    # ---------- Du toan XD ----------
    def dt_group(self, prefix):
        ws, n = self.dt, last_row(self.dt, 6)
        for r in range(8, n + 1):
            if val(ws, r, 5) == "HM" and str(val(ws, r, 6)).strip().startswith(prefix):
                hm = r
                break
        else:
            sys.exit(f"Không thấy nhóm bắt đầu bằng '{prefix}' trong Du toan XD")
        tc = next(r for r in range(hm + 1, n + 2) if val(ws, r, 5) == "TC")
        last_item = max([r for r in range(hm + 1, tc) if val(ws, r, 4) or val(ws, r, 6)] or [hm])
        return hm, tc, last_item

    def dt_new_row(self, prefix, it):
        ws = self.dt
        hm, tc, last_item = self.dt_group(prefix)
        new = last_item + 1
        if new >= tc:  # không còn dòng trống dự phòng: chèn dòng mới trước dòng cộng nhóm
            ws.Rows(tc).Insert()
            tc += 1
            for col in "UVWXY":
                ws.Range(f"{col}{tc}").Formula = f"=SUM({col}{hm}:{col}{new})"
        src = last_item if last_item > hm else hm
        ws.Range(f"A{src}:BD{src}").Copy()
        ws.Range(f"A{new}:BD{new}").PasteSpecial(PASTE_FORMATS)
        if src != hm:
            ws.Range(f"U{src}:Y{src}").Copy(ws.Range(f"U{new}:Y{new}"))
        ws.Application.CutCopyMode = False
        ids = [num(val(ws, r, 1)) for r in range(8, last_row(ws, 1) + 1) if isinstance(val(ws, r, 1), (int, float))]
        ws.Cells(new, 1).Value2 = int(max(ids)) + 1
        ws.Cells(new, 2).Value2 = int(num(val(ws, last_item, 2))) + 1
        ws.Cells(new, 3).Value2 = ""
        ws.Cells(new, 4).Value2 = it["ma_dm"]
        ws.Cells(new, 5).Value2 = it["ma_dg"]
        ws.Cells(new, 6).Value2 = it["noi_dung"]
        ws.Cells(new, 7).Value2 = it["dvt"]
        ws.Cells(new, 8).Value2 = it.get("kl")
        ws.Cells(new, 34).Value2 = "BXD_XD+LD+SC_TT38-2026"
        return new

    # ---------- Don gia XD ----------
    def dg_block(self, drow, it):
        ws, vt = self.dg, self.vt
        vl, nc, may = it.get("vl", []), it.get("nc", []), it.get("may", [])
        vlk, mk = it.get("vl_khac"), it.get("may_khac")
        n = 1 + (1 + len(vl) + (1 if vlk else 0) if (vl or vlk) else 0) + (1 + len(nc) if nc else 0) \
            + (1 + len(may) + (1 if mk else 0) if (may or mk) else 0) + 11
        # điểm chèn: ngay sau dòng 'TC' (Đơn giá dự thầu) cuối cùng của cột A. Không dùng End(xlUp) vì
        # kết quả bị lệch trên file này (đã gặp: chèn nhầm vào giữa khối cuối).
        col_a = ws.Range(f"A1:A{ws.UsedRange.Rows.Count + 5}").Value2
        s = max(i for i, row in enumerate(col_a, start=1) if row[0] == "TC") + 1
        if val(ws, s, 7) not in (None, ""):
            sys.exit(f"Don gia XD dòng {s} không trống, dừng để khỏi ghi đè")
        ws.Rows(f"{s}:{s + n - 1}").Insert()
        # định dạng mẫu từ khối đầu tiên (dòng 8..30 của Don gia XD)
        def fmt(src, dst):
            ws.Range(f"A{src}:AX{src}").Copy()
            ws.Range(f"A{dst}:AX{dst}").PasteSpecial(PASTE_FORMATS)
        r = s
        fmt(8, r)
        ws.Cells(r, 1).Formula = f"='Du toan XD'!A{drow}"
        ws.Cells(r, 2).Formula = f"='Du toan XD'!B{drow}"
        ws.Cells(r, 4).Value2, ws.Cells(r, 5).Value2 = it["ma_dm"], it["ma_dg"]
        ws.Cells(r, 7).Formula, ws.Cells(r, 8).Formula, ws.Cells(r, 9).Formula = (
            f"='Du toan XD'!F{drow}", f"='Du toan XD'!G{drow}", f"='Du toan XD'!H{drow}")
        head, sec = r, {}
        r += 1
        vtcache = {}
        def rows_for(kind, items, khac, key, label, kfmt, kcode):
            nonlocal r
            h = r
            fmt(9 if key == "vl" else 15 if key == "nc" else 17, h)
            ws.Cells(h, 7).Value2 = label
            first = h + 1
            for x in items:
                r += 1
                fmt(10 if key == "vl" else 16 if key == "nc" else 18, r)
                prow = self.vt_ensure(key, x)
                ws.Cells(r, 6).Value2 = x["msvt"]
                ws.Cells(r, 7).Value2 = x.get("ten") or val(vt, prow, 3)
                ws.Cells(r, 8).Value2 = x.get("dvt") or val(vt, prow, 4)
                ws.Cells(r, 10).Value2 = x["dm"]
                ws.Cells(r, 11).Formula = f"='TH vat tu XD'!G{prow}"
                ws.Cells(r, 13).Formula = f"=IF(L{r}=0,J{r}*K{r},J{r}*K{r}*L{r})"
                ws.Cells(r, 14).Formula = f"=IF(L{r}=0,I{head}*J{r},I{head}*J{r}*L{r})"
                vtcache[(key, x["msvt"])] = (r, x["dm"], prow)
            last = r
            if khac:
                r += 1
                fmt(14 if key == "vl" else 19, r)
                ws.Cells(r, 6).Value2, ws.Cells(r, 7).Value2 = kcode, kfmt
                ws.Cells(r, 8).Value2, ws.Cells(r, 10).Value2 = "%", khac
                ws.Cells(r, 13).Formula = f"=SUM(M{first}:M{last})*J{r}%"
                for rr in range(first, last + 1):
                    if key != "nc":
                        ws.Cells(rr, 15).Formula = f"=J{r}%*N{rr}"
                last = r
            ws.Cells(h, 13).Formula = f"=ROUND(SUM(M{first}:M{last}),Config!C103)"
            sec[key] = h
            r += 1
        if vl or vlk: rows_for("vl", vl, vlk, "vl", "Vật liệu", "Vật liệu khác", "V19999")
        if nc: rows_for("nc", nc, None, "nc", "Nhân công", None, None)
        if may or mk: rows_for("m", may, mk, "m", "Máy thi công", "Máy khác", "M9999")
        t = r
        ws.Range(f"A20:AX30").Copy()
        ws.Range(f"A{t}:AX{t + 10}").PasteSpecial(-4104)  # xlPasteAll: công thức tương đối của đuôi 11 dòng
        ws.Application.CutCopyMode = False
        parts = [f"M{sec[k]}" for k in ("vl", "nc", "m") if k in sec]
        ws.Cells(t, 13).Formula = "=" + "+".join(parts)
        if "vl" in sec: ws.Cells(head, 16).Formula = f"=M{sec['vl']}"
        if "nc" in sec: ws.Cells(head, 18).Formula = f"=M{sec['nc']}"
        if "m" in sec: ws.Cells(head, 19).Formula = f"=M{sec['m']}"
        info = {"head": head, "sec": sec, "direct": t, "tc": t + 10, "mats": vtcache}
        return info

    def link_dt(self, drow, info):
        ws, sec = self.dt, info["sec"]
        for col in "PQRST":
            ws.Range(f"{col}{drow}").ClearContents()
        if "vl" in sec: ws.Range(f"P{drow}").Formula = f"='Don gia XD'!M{sec['vl']}"
        if "nc" in sec: ws.Range(f"R{drow}").Formula = f"='Don gia XD'!M{sec['nc']}"
        if "m" in sec: ws.Range(f"S{drow}").Formula = f"='Don gia XD'!M{sec['m']}"
        ws.Range(f"T{drow}").Formula = f"='Don gia XD'!M{info['tc']}"

    def verify(self, it, info):
        """Tính lại chi phí trực tiếp bằng Python từ định mức x giá đọc từ TH vat tu XD."""
        dg, vt = self.dg, self.vt
        def price(prow): return num(val(vt, prow, 7))
        tot = {}
        for key, items, khac in (("vl", it.get("vl", []), it.get("vl_khac")),
                                 ("nc", it.get("nc", []), None), ("m", it.get("may", []), it.get("may_khac"))):
            if key not in info["sec"]:
                continue
            base = 0.0
            for x in items:
                rr, dm, prow = info["mats"][(key, x["msvt"])]
                base += dm * price(prow)
            tot[key] = base * (1 + (khac or 0) / 100)
        exp = sum(tot.values())
        got = num(val(dg, info["direct"], 13))
        ok = abs(exp - got) <= 3  # ROUND ở từng nhóm, sai số vài đồng
        self.checks.append((it["ma_dm"], exp, got, ok))
        return ok


def main(spec_path):
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8-sig"))
    src, out = Path(spec["file_in"]), Path(spec["file_out"])
    if out.exists():
        sys.exit(f"{out} đã tồn tại, không ghi đè")
    shutil.copyfile(src, out)
    xl = win32.Dispatch("Excel.Application")
    xl.Visible, xl.DisplayAlerts, xl.AutomationSecurity, xl.EnableEvents = False, False, 3, False
    try:
        b = Book(xl, out)
        for it in spec["items"]:
            drow = b.dt_new_row(it["nhom"], it)
            info = b.dg_block(drow, it)
            b.link_dt(drow, info)
            xl.Calculate()
            b.verify(it, info)
            print(f"+ {it['ma_dm']}: Du toan XD dòng {drow}, khối đơn giá Don gia XD dòng {info['head']}-{info['tc']}")
        xl.Calculate()
        print("Kiểm số học (chi phí trực tiếp, đ/đơn vị): mã | tính lại | trong file | khớp")
        for c in b.checks:
            print("  ", c[0], round(c[1]), round(c[2]), "OK" if c[3] else "LỆCH")
        extra = []
        for s in b.wb.Worksheets:
            try:
                n = s.UsedRange.SpecialCells(-4123, 16).Count
            except Exception:
                n = 0
            if n > BASELINE_ERR.get(s.Name, 0):
                extra.append(f"{s.Name}: {n} (nền {BASELINE_ERR.get(s.Name, 0)})")
        print("Ô lỗi vượt nền của mẫu:", extra or "không có")
        b.wb.SaveAs(str(out), 52)
        b.wb.Close(False)
    finally:
        xl.Quit()
    print("Đã lưu:", out)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
