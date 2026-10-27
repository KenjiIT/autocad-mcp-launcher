"""Write the block catalogue page (Markdown) for the autocad-block-library skill.

    python build_block_catalog.py CATALOG_JSON INDEX_JSON OUT_MD

CATALOG_JSON is the file ``extract_sample_blocks.py --catalog-json`` writes;
INDEX_JSON is ``blocks/index.json``.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sample_blocks import OTHER_GROUPS, SELECTED  # noqa: E402

MM_PER_UNIT = {1: 25.4, 2: 304.8, 4: 1.0, 5: 10.0, 6: 1000.0}
UNIT_NAMES = {0: "không đơn vị", 1: "inch", 2: "feet", 4: "mm", 5: "cm", 6: "m"}
VIEW_NAMES = {"plan": "mặt bằng", "elevation": "mặt đứng/cắt", "symbol": "ký hiệu"}


def cell(text: str) -> str:
    return text.replace("|", "/").replace("\ufffd", "?")


def main() -> None:
    catalog = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    index = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    by_source = {(e["source_file"], e["source_block"]): (name, e) for name, e in index.items()}
    total = sum(len(v["blocks"]) for v in catalog.values())
    lines = [
        "# Danh mục block của AutoCAD LT (bản vẽ mẫu đi kèm)",
        "",
        f"Nguồn: các bản vẽ mẫu trong `C:\\Program Files\\Autodesk\\AutoCAD LT <năm>\\Sample\\en-us\\`. "
        f"Tổng cộng {total} block trong {len(catalog)} tệp. {len(index)} block hữu ích cho bản vẽ xây dựng "
        "đã được tách thành tệp riêng trong `blocks\\` (cột **Tệp thư viện**); các block còn lại chỉ được liệt kê.",
        "",
        "Cách đọc: *Kích thước* là khung bao của block tính ra mm, ở tỉ lệ 1 và góc xoay 0. *Điểm chèn* của block "
        "nằm ở gốc (0,0) của khung đó, nên cột **Khung bao** cho biết gốc nằm ở đâu so với hình "
        "(`x1,y1 → x2,y2`, mm). Loại hình (mặt bằng, mặt đứng, ký hiệu) suy ra từ tên và kích thước, chưa kiểm bằng mắt từng block.",
        "",
    ]
    for key, data in catalog.items():
        units = UNIT_NAMES.get(data["insunits"], data["insunits"])
        blocks = data["blocks"]
        filename = key.split("/", 1)[1]
        selected_here = [b for b in blocks if (key, b["name"]) in by_source]
        lines.append(f"## {key}")
        lines.append("")
        description = OTHER_GROUPS.get(filename, "")
        if not description and filename.endswith(" - Imperial.dwg"):
            description = f"Bản hệ inch của {filename.replace('Imperial', 'Metric')}; dùng bản hệ mét"
        lines.append(f"Đơn vị của tệp: {units}. {len(blocks)} block; {len(selected_here)} đã tách thành tệp thư viện."
                     + (f" Nội dung: {description}." if description and not selected_here else ""))
        lines.append("")
        if selected_here:
            lines += ["| Block gốc | Tệp thư viện | Ý nghĩa | Loại | Kích thước mm | Khung bao mm |", "|---|---|---|---|---|---|"]
            for block in blocks:
                found = by_source.get((key, block["name"]))
                if not found:
                    lines.append(f"| {cell(block['name'])} | — | khối phụ trợ của block khác, không dùng riêng | — | — | — |")
                    continue
                name, entry = found
                size = "×".join(str(v) for v in entry["size_mm"])
                box = " → ".join(f"{entry['bbox_mm'][i]:g},{entry['bbox_mm'][i + 1]:g}" for i in (0, 2))
                dynamic = " (block động)" if entry.get("dynamic") else ""
                lines.append(f"| {cell(block['name'])} | `{name}` | {cell(entry['meaning'])}{dynamic} | "
                             f"{VIEW_NAMES.get(entry['view'], entry['view'])} | {size} | {box} |")
        else:
            names = ", ".join(cell(b["name"]) for b in blocks) or "(không có block)"
            lines.append(f"Chưa tách thành tệp thư viện. Tên block: {names}.")
        lines.append("")
    Path(sys.argv[3]).write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"{len(lines)} dòng")


if __name__ == "__main__":
    main()
