"""Split a folder of DWG block packs into one "kho" (store) of the block library.

Needs a running AutoCAD LT with this repository's dispatcher trusted, like
extract_sample_blocks.py.  Each pack is opened in LT (and left open; type CLOSEALL
afterwards), its named blocks are catalogued, the usable ones are written one per file
to ``<library>/<kho>/`` and described in ``<library>/<kho>/index.json``.

    python import_block_pack.py --kho dwgshare --packs DIR [--library DIR] [--catalog-json FILE]

``DIR`` holds the pack DWGs under ASCII names listed in PACKS below.  Re-running skips
files that already exist, so an interrupted run can simply be started again.

With --rebase it imports the rest (right size, geometry far away) after moving the base point to the middle of
the front edge, by inserting a copy, exploding it and writing the pieces (block_export_rebased).

A block is usable when its geometry sits near its own base point (otherwise inserting it
at (x, y) would drop the drawing metres away), its size is between 150 mm and 12 m and it
has 3 to 1500 entities.  The packs name blocks "DWGshare.com_<n>", so the only meaning a
file gets is its pack's theme: say so, and check by screenshot after inserting.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "autocad-beiming-mcp-custom" / "src"))
sys.path.insert(0, str(REPO / "lt-adapter" / "py"))
os.environ.setdefault("AUTOCAD_MCP_BACKEND", "file_ipc")

from extract_sample_blocks import catalog_blocks, library_id, open_and_wait, round_mm  # noqa: E402

# file stem -> (category in the file name, what the pack is, in Vietnamese)
PACKS = {
    "1_sofa": ("SOFA", "bộ sofa, phòng khách (mặt bằng bố trí)"),
    "2_coffee_bar": ("TABLE", "bàn cà phê, quầy bar và ghế quanh quầy"),
    "3_office": ("OFFICE", "nội thất văn phòng, phòng họp"),
    "4_decor_light_human": ("DECOR", "trang trí, đèn, hình người"),
    "5_kitchen_bed_bath": ("KBB", "bếp, giường phòng ngủ, thiết bị vệ sinh"),
    "6_branded": ("BRAND", "bộ sưu tập nội thất, phụ kiện nhỏ"),
    "7_gym": ("GYM", "thiết bị thể thao, giải trí, phòng gym"),
    "8_stairs": ("STAIR", "cầu thang, thang cuốn, lối đi (sơ đồ)"),
    "9_landscape": ("LAND", "cây, đá, cảnh quan sân vườn"),
}
NEAR_LIMIT_MM = 12000.0
MIN_SIDE_MM, MAX_SIDE_MM = 150.0, 12000.0
MIN_ENTITIES, MAX_ENTITIES = 3, 1500


def usable(block: dict) -> bool:
    if "min" not in block or "max" not in block:
        return False
    low, high = block["min"], block["max"]
    if max(abs(low[0]), abs(low[1]), abs(high[0]), abs(high[1])) > NEAR_LIMIT_MM:
        return False
    width, depth = high[0] - low[0], high[1] - low[1]
    if not (MIN_SIDE_MM <= max(width, depth) <= MAX_SIDE_MM):
        return False
    return MIN_ENTITIES <= block.get("entities", 0) <= MAX_ENTITIES


def rebase_candidate(block: dict) -> bool:
    """A block of the right size whose geometry lies far from its base point (usable only after rebasing)."""
    if "min" not in block or "max" not in block or usable(block):
        return False
    low, high = block["min"], block["max"]
    if not (MIN_SIDE_MM <= max(high[0] - low[0], high[1] - low[1]) <= MAX_SIDE_MM):
        return False
    return MIN_ENTITIES <= block.get("entities", 0) <= MAX_ENTITIES


def block_number(name: str) -> str:
    found = re.search(r"(\d+)\s*$", name)
    if found:
        return f"{int(found.group(1)):04d}"
    return re.sub(r"[^A-Za-z0-9]+", "", name)[:12].upper() or "X"


async def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--kho", required=True, help="store name = sub-folder of the library, e.g. dwgshare")
    parser.add_argument("--packs", type=Path, required=True)
    parser.add_argument("--library", type=Path, default=REPO / "blocks")
    parser.add_argument("--catalog-json", type=Path, default=None, help="reuse a saved catalogue instead of reading LT")
    parser.add_argument("--prefix", default="DS")
    parser.add_argument("--only", default=None, help="comma list of pack stems to run")
    parser.add_argument("--rebase", action="store_true",
                        help="import the blocks whose geometry is far from their base point, moving the base point "
                             "to the middle of the front edge (x = centre, y = lowest point)")
    parser.add_argument("--limit", type=int, default=None, help="at most this many blocks per pack (trial runs)")
    args = parser.parse_args()
    folder = (args.library / args.kho).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    os.environ["AUTOCAD_MCP_BLOCK_LIBRARY"] = str(folder)

    from lt_adapter.bootstrap import install
    install()
    from autocad_mcp.backends.lt_file_ipc import LtFileIPCBackend

    index_path = folder / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.is_file() else {}
    saved = json.loads(args.catalog_json.read_text(encoding="utf-8")) if args.catalog_json and args.catalog_json.is_file() else {}
    only = set(args.only.split(",")) if args.only else None
    backend = LtFileIPCBackend()
    seen = {entry["source_block"] for entry in index.values()}

    for stem, (category, theme) in PACKS.items():
        path = args.packs / f"{stem}.dwg"
        if not path.is_file() or (only and stem not in only):
            continue
        await open_and_wait(backend, path, timeout=240)
        key = path.name
        if key in saved:
            blocks, units = saved[key]["blocks"], saved[key]["insunits"]
        else:
            variables = await backend.drawing_get_variables(["INSUNITS"])
            units = int(variables.payload["INSUNITS"]) if variables.ok else 0
            blocks = await catalog_blocks(backend)
        if units != 4:
            print(f"!! {key}: đơn vị {units}, không phải mm; bỏ qua gói này")
            continue
        pick = rebase_candidate if args.rebase else usable
        wanted = [b for b in blocks if pick(b) and b["name"] not in seen]
        if args.limit:
            wanted = wanted[:args.limit]
        print(f"{key}: {len(blocks)} block, {len(wanted)} dùng được", flush=True)
        for position, block in enumerate(wanted, 1):
            low, high = block["min"], block["max"]
            file_id = library_id(f"{args.prefix}-{category}-{block_number(block['name'])}", low, high)
            started = time.time()
            if not (folder / f"{file_id}.dwg").is_file():
                if args.rebase:
                    result = await backend.block_export_rebased(
                        block["name"], file_id, -(low[0] + high[0]) / 2, -low[1])
                else:
                    result = await backend.block_export(block["name"], file_id)
                if not result.ok:
                    print(f"!! {key}: {block['name']}: {result.error}", flush=True)
                    if "instance changed" in str(result.error):
                        raise SystemExit("AutoCAD LT đã đổi hoặc khởi động lại; dừng. Kiểm tra LT rồi chạy lại (tệp đã có được giữ).")
                    continue
            seen.add(block["name"])
            width, depth = high[0] - low[0], high[1] - low[1]
            if args.rebase:
                low, high = [-width / 2, 0.0], [width / 2, depth]
            index[file_id] = {
                "source_file": key, "source_block": block["name"], "kho": args.kho, "category": category,
                "view": "unverified",
                "meaning": f"Gói {theme}; khối {block['name']}, chưa biết là vật gì, xem ảnh chụp sau khi chèn",
                "units": "millimeters", "mm_per_unit": 1.0,
                "size_mm": [round_mm(width), round_mm(depth)],
                "bbox_mm": [round(low[0], 1), round(low[1], 1), round(high[0], 1), round(high[1], 1)],
                "dynamic": False, "rebased": bool(args.rebase),
            }
            if position % 20 == 0 or position == len(wanted):
                index_path.write_text(json.dumps(index, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
                print(f"  {position}/{len(wanted)} ({time.time() - started:.1f}s/block)", flush=True)
        index_path.write_text(json.dumps(index, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    print(f"{len(index)} block trong kho {args.kho}")


if __name__ == "__main__":
    asyncio.run(main())
