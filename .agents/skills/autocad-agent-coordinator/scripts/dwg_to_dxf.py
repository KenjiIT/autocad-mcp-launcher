"""Đổi bản sao DWG sang DXF bằng LibreDWG (dwg2dxf) rồi tóm tắt bằng ezdxf.

Dùng khi cần đọc nhiều đối tượng của một bản vẽ (từ khoảng 100 đối tượng trở lên, bóc khối lượng,
lấy đường biên hatch) mà không muốn đổ dữ liệu qua MCP. Không đụng file DWG gốc: script chép nó
sang tên ASCII trong thư mục tạm rồi đổi.

    py -3 dwg_to_dxf.py <file.dwg> [--out <thư-mục>]

Tìm dwg2dxf theo thứ tự: biến môi trường LIBREDWG_DIR, PATH, %USERPROFILE%/tools/libredwg/bin.
Cần `pip install ezdxf`. Kết quả: in đường dẫn DXF và bảng tóm tắt (số đối tượng theo loại, hatch,
layer). Lưu ý: LibreDWG đọc DWG đời mới chưa hoàn chỉnh (cảnh báo "Unstable Class" là bình thường);
đối chiếu số lượng với bản vẽ gốc trước khi dùng làm căn cứ.
"""
import argparse
import collections
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def find_dwg2dxf():
    candidates = []
    if os.environ.get("LIBREDWG_DIR"):
        base = Path(os.environ["LIBREDWG_DIR"])
        candidates += [base / "dwg2dxf.exe", base / "bin" / "dwg2dxf.exe"]
    found = shutil.which("dwg2dxf")
    if found:
        candidates.append(Path(found))
    candidates.append(Path.home() / "tools" / "libredwg" / "bin" / "dwg2dxf.exe")
    for c in candidates:
        if c.is_file():
            return c
    sys.exit("Không thấy dwg2dxf. Tải libredwg-<bản>-win64.zip ở github.com/LibreDWG/libredwg/releases, "
             "giải nén vào %USERPROFILE%/tools/libredwg/bin hoặc đặt biến LIBREDWG_DIR.")


def convert(dwg, out_dir):
    exe = find_dwg2dxf()
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "in.dwg"
        shutil.copyfile(dwg, src)  # tên ASCII, không động vào file gốc
        dxf_tmp = Path(tmp) / "out.dxf"
        proc = subprocess.run([str(exe), "-y", "-o", str(dxf_tmp), str(src)],
                              capture_output=True, text=True, errors="replace")
        if not dxf_tmp.is_file() or dxf_tmp.stat().st_size == 0:
            sys.exit("dwg2dxf không tạo được DXF:\n" + (proc.stderr or proc.stdout)[-800:])
        target = out_dir / (dwg.stem + ".dxf")
        shutil.copyfile(dxf_tmp, target)
    return target


def summarize(dxf):
    from ezdxf import recover
    doc, auditor = recover.readfile(str(dxf))
    msp = doc.modelspace()
    kinds = collections.Counter(e.dxftype() for e in msp)
    hatches = [e for e in msp if e.dxftype() == "HATCH"]
    print(f"DXF: {dxf}")
    print(f"Phiên bản {doc.dxfversion} | {sum(kinds.values())} đối tượng | lỗi audit {len(auditor.errors)}")
    print("Theo loại:", dict(kinds.most_common()))
    print(f"HATCH: {len(hatches)}, có đường biên: {sum(1 for h in hatches if len(h.paths) > 0)}")
    print(f"Layer: {len(doc.layers)} | block: {len(doc.blocks)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dwg", type=Path)
    ap.add_argument("--out", type=Path, default=Path(tempfile.gettempdir()) / "dwg2dxf_out",
                    help="thư mục ghi DXF (mặc định: thư mục tạm, không phải thư mục dự án)")
    args = ap.parse_args()
    if not args.dwg.is_file():
        sys.exit(f"Không thấy file: {args.dwg}")
    summarize(convert(args.dwg, args.out))


if __name__ == "__main__":
    main()
