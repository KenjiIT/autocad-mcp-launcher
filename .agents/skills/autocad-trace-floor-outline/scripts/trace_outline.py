#!/usr/bin/env python
"""Truy đường bao một mặt bằng tầng từ các đoạn tường rời trong bản sao DXF.

Chỉ ĐỌC file DXF (bản sao do drawing.save_as_dxf xuất ra). Không mở, không sửa DWG gốc.

Thuật toán: tô các LINE/LWPOLYLINE/ARC của layer đã chọn lên lưới --res mm, nở ra
--close mm để khép khe cửa, tô đầy phần ngoài từ rìa, co lại, lấy biên ngoài bằng
contour, rồi đơn giản hóa (Douglas-Peucker). Tùy chọn bám vào các trục (--snap-x/--snap-y)
và làm thẳng các cạnh.

Kết quả là đường bao SUY RA từ hình học, không phải đối tượng có sẵn trong bản vẽ.

Ví dụ:
  python -I trace_outline.py --dxf a203_copy.dxf \
     --layers A-FLOR-WALL A-FLOR-WALL-1 A-FLOR-OTLN \
     --offset -33589.5 -1094766.4 --bbox 5900 300 107100 31000 \
     --snap-x 6000 14345 22695 106995 --snap-y 400 11000 27900 30900 --out out_dir

--offset: dịch tọa độ nguồn sang hệ đích (x_moi = x_nguon + dx). --bbox cho theo hệ ĐÍCH.
Cần: ezdxf, numpy, matplotlib (có sẵn trong .venv của autocad-beiming-mcp-custom).
"""
import argparse
import json
import math
import os

import ezdxf
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def collect_points(entity, dx, dy):
    t = entity.dxftype()
    if t == "LINE":
        return [(entity.dxf.start.x + dx, entity.dxf.start.y + dy),
                (entity.dxf.end.x + dx, entity.dxf.end.y + dy)]
    if t == "LWPOLYLINE":
        return [(p[0] + dx, p[1] + dy) for p in entity.get_points()]
    if t == "ARC":
        c, r = entity.dxf.center, entity.dxf.radius
        a0 = math.radians(entity.dxf.start_angle)
        a1 = math.radians(entity.dxf.end_angle)
        if a1 < a0:
            a1 += 2 * math.pi
        return [(c.x + dx + r * math.cos(a0 + (a1 - a0) * i / 36),
                 c.y + dy + r * math.sin(a0 + (a1 - a0) * i / 36)) for i in range(37)]
    return []


def dilate(m, k):
    o = m.copy()
    for _ in range(k):
        n = o.copy()
        n[1:] |= o[:-1]; n[:-1] |= o[1:]; n[:, 1:] |= o[:, :-1]; n[:, :-1] |= o[:, 1:]
        n[1:, 1:] |= o[:-1, :-1]; n[:-1, :-1] |= o[1:, 1:]
        n[1:, :-1] |= o[:-1, 1:]; n[:-1, 1:] |= o[1:, :-1]
        o = n
    return o


def rdp(p, eps):
    if len(p) < 3:
        return list(p)
    a, b = np.array(p[0]), np.array(p[-1])
    d = b - a
    length = float(np.hypot(*d))
    dist = [abs(d[0] * (q[1] - a[1]) - d[1] * (q[0] - a[0])) / length if length
            else float(np.hypot(q[0] - a[0], q[1] - a[1])) for q in p[1:-1]]
    i = int(np.argmax(dist)) + 1
    if dist[i - 1] > eps:
        return rdp(p[:i + 1], eps)[:-1] + rdp(p[i:], eps)
    return [p[0], p[-1]]


def area(poly):
    s = 0.0
    for i in range(len(poly)):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % len(poly)]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2 / 1e6  # m2 khi don vi mm


def dist_to_poly(pt, poly):
    best = 1e18
    for i in range(len(poly)):
        ax, ay = poly[i]
        bx, by = poly[(i + 1) % len(poly)]
        dx, dy = bx - ax, by - ay
        den = dx * dx + dy * dy
        t = 0 if den == 0 else max(0, min(1, ((pt[0] - ax) * dx + (pt[1] - ay) * dy) / den))
        best = min(best, math.hypot(pt[0] - (ax + t * dx), pt[1] - (ay + t * dy)))
    return best


def snap(poly, xs, ys, tol):
    def near(v, axes):
        if not axes:
            return v
        c = min(axes, key=lambda a: abs(a - v))
        return c if abs(c - v) <= tol else v
    out = []
    for x, y in poly:
        q = (near(x, xs), near(y, ys))
        if not out or q != out[-1]:
            out.append(q)
    if len(out) > 1 and out[0] == out[-1]:
        out.pop()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dxf", required=True)
    ap.add_argument("--layers", nargs="+", required=True)
    ap.add_argument("--offset", nargs=2, type=float, default=[0, 0])
    ap.add_argument("--bbox", nargs=4, type=float, required=True, help="x0 y0 x1 y1 (he dich)")
    ap.add_argument("--res", type=float, default=100.0)
    ap.add_argument("--close", type=float, default=800.0, help="mm de khep khe cua")
    ap.add_argument("--eps", type=float, default=120.0, help="mm don gian hoa")
    ap.add_argument("--snap-x", nargs="*", type=float, default=[])
    ap.add_argument("--snap-y", nargs="*", type=float, default=[])
    ap.add_argument("--snap-tol", type=float, default=500.0)
    ap.add_argument("--snap-eps", type=float, default=600.0, help="mm don gian hoa truoc khi snap")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    msp = ezdxf.readfile(a.dxf).modelspace()
    dx, dy = a.offset
    x0, y0, x1, y1 = a.bbox
    pad = 1000
    gx0, gy0, gx1, gy1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
    R = a.res
    W, H = int((gx1 - gx0) // R) + 1, int((gy1 - gy0) // R) + 1
    mask = np.zeros((H, W), bool)
    used = {}
    for e in msp:
        if e.dxf.layer not in a.layers:
            continue
        pts = collect_points(e, dx, dy)
        if not pts or not all(x0 <= p[0] <= x1 and y0 <= p[1] <= y1 for p in pts):
            continue
        used[e.dxf.layer] = used.get(e.dxf.layer, 0) + 1
        for p, q in zip(pts, pts[1:]):
            n = max(2, int(math.hypot(q[0] - p[0], q[1] - p[1]) / (R / 2)))
            for k in range(n + 1):
                t = k / n
                i = int((p[1] + (q[1] - p[1]) * t - gy0) / R)
                j = int((p[0] + (q[0] - p[0]) * t - gx0) / R)
                if 0 <= i < H and 0 <= j < W:
                    mask[i, j] = True
    print("doi tuong dung theo layer:", used, "| diem anh:", int(mask.sum()))
    if not mask.any():
        raise SystemExit("Khong co doi tuong nao trong bbox/layer da chon.")

    K = max(1, int(round(a.close / R)))
    c = dilate(mask, K)
    front = np.zeros_like(c)
    front[0, :] = front[-1, :] = front[:, 0] = front[:, -1] = True
    front &= ~c
    while True:
        n = (dilate(front, 1) & ~c) | front
        if (n == front).all():
            break
        front = n
    solid = ~front                   # phan trong + phan da no ra
    solid = ~dilate(~solid, K)       # co lai K o
    fig = plt.figure()
    cs = plt.contour(np.arange(W) * R + gx0, np.arange(H) * R + gy0, solid.astype(float), [0.5])
    plt.close(fig)
    paths = sorted(cs.allsegs[0], key=lambda p: -len(p))
    if not paths:
        raise SystemExit("Khong truy duoc bien ngoai.")
    print("so contour:", len(paths), "(chi dung contour lon nhat; kiem tra cac khoi roi neu >1)")
    main_path = [tuple(map(float, q)) for q in paths[0]]
    closed = main_path[:-1] if main_path[0] == main_path[-1] else main_path
    k = max(range(len(closed)), key=lambda i: (closed[i][0] - closed[0][0]) ** 2 + (closed[i][1] - closed[0][1]) ** 2)

    def simplify(eps):
        return rdp(closed[:k + 1], eps)[:-1] + rdp(closed[k:] + [closed[0]], eps)[:-1]

    traced = simplify(a.eps)
    res = {"traced": traced, "traced_area_m2": round(area(traced), 1), "offset": [dx, dy]}
    print("bien truy duoc:", len(traced), "dinh, dien tich", res["traced_area_m2"], "m2")
    if a.snap_x or a.snap_y:
        coarse = simplify(a.snap_eps)
        snapped = snap(coarse, a.snap_x, a.snap_y, a.snap_tol)
        dev = [dist_to_poly(p, snapped) for p in traced]
        res["snapped"] = snapped
        res["snapped_area_m2"] = round(area(snapped), 1)
        res["max_dev_mm"] = round(max(dev))
        res["far_points"] = [(round(p[0]), round(p[1]), round(d)) for p, d in zip(traced, dev) if d > a.snap_tol]
        print("bam truc:", len(snapped), "dinh, dien tich", res["snapped_area_m2"], "m2,",
              "lech lon nhat", res["max_dev_mm"], "mm;", len(res["far_points"]), "dinh lech >", a.snap_tol, "mm")
    with open(os.path.join(a.out, "outline.json"), "w") as f:
        json.dump(res, f, indent=1)
    fig, ax = plt.subplots(figsize=(22, 9))
    ax.imshow(mask, origin="lower", extent=[gx0, gx1, gy0, gy1], cmap="Greys", alpha=.5)
    ax.plot([p[0] for p in traced + traced[:1]], [p[1] for p in traced + traced[:1]], "r-", lw=1.5, label="truy duoc")
    if "snapped" in res:
        s = res["snapped"]
        ax.plot([p[0] for p in s + s[:1]], [p[1] for p in s + s[:1]], "b-", lw=3, label="bam truc")
    ax.set_aspect("equal"); ax.grid(True, alpha=.3); ax.legend()
    plt.tight_layout(); plt.savefig(os.path.join(a.out, "outline_check.png"), dpi=55)
    print("da ghi:", os.path.join(a.out, "outline.json"), "va outline_check.png")


if __name__ == "__main__":
    main()
