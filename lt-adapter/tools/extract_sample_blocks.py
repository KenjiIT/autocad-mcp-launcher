"""Catalogue AutoCAD LT's sample block drawings and copy the chosen blocks into blocks/.

Needs a running AutoCAD LT with this repository's dispatcher trusted (the same setup
the MCP server uses).  The sample drawings are copied to a work folder first, so the
originals under Program Files stay untouched.  Every sample is opened in LT and left
open (type CLOSEALL afterwards; only modified drawings ask to be saved).

    python extract_sample_blocks.py [--samples DIR] [--library DIR] [--catalog-json FILE]

Writes <library>/<id>.dwg per selected block, <library>/index.json (what each file is)
and, with --catalog-json, the full list of every block in every sample drawing.
"""
from __future__ import annotations

import argparse
import asyncio
import glob
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "autocad-beiming-mcp-custom" / "src"))
sys.path.insert(0, str(REPO / "lt-adapter" / "py"))
os.environ.setdefault("AUTOCAD_MCP_BACKEND", "file_ipc")

from sample_blocks import SELECTED  # noqa: E402

MM_PER_UNIT = {1: 25.4, 2: 304.8, 4: 1.0, 5: 10.0, 6: 1000.0}
UNIT_NAMES = {1: "inches", 2: "feet", 4: "millimeters", 5: "centimeters", 6: "meters"}


def default_samples() -> Path:
    found = sorted(glob.glob(r"C:\Program Files\Autodesk\AutoCAD LT *\Sample\en-us"))
    if not found:
        raise SystemExit("Không tìm thấy thư mục Sample\\en-us của AutoCAD LT; dùng --samples.")
    return Path(found[-1])


def round_mm(value: float) -> int:
    """Nearest 5 mm for real objects, nearest 1 mm (at least 1) for small drawing symbols."""
    if value >= 50:
        return int(round(value / 5.0)) * 5
    return max(1, int(round(value)))


def library_id(base_id: str, low: list, high: list) -> str:
    return f"{base_id}-{round_mm(high[0] - low[0])}x{round_mm(high[1] - low[1])}"


async def open_and_wait(backend, path: Path) -> None:
    os.startfile(str(path))
    deadline = time.time() + 90
    while time.time() < deadline:
        await asyncio.sleep(2)
        ready = await backend.ensure_ready()
        if ready.ok and ready.payload["autocad"]["active_document"].lower() == path.name.lower():
            return
    raise RuntimeError(f"{path.name} không thành bản vẽ đang hoạt động trong LT")


async def catalog_blocks(backend) -> list[dict]:
    blocks, start = [], 0
    while True:
        page = await backend.block_catalog(start, 25)
        if not page.ok:
            raise RuntimeError(page.error)
        blocks += page.payload["blocks"]
        if page.payload["next"] is None:
            return blocks
        start = page.payload["next"]


async def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--samples", type=Path, default=None)
    parser.add_argument("--library", type=Path, default=REPO / "blocks")
    parser.add_argument("--catalog-json", type=Path, default=None)
    args = parser.parse_args()
    samples = args.samples or default_samples()
    library = args.library.resolve()
    library.mkdir(parents=True, exist_ok=True)
    os.environ["AUTOCAD_MCP_BLOCK_LIBRARY"] = str(library)

    from lt_adapter.bootstrap import install
    install()
    from autocad_mcp.backends.lt_file_ipc import LtFileIPCBackend

    work = Path(tempfile.mkdtemp(prefix="autocad-samples-"))
    for sub in ("DesignCenter", "Dynamic Blocks"):
        shutil.copytree(samples / sub, work / sub)
    for path in work.rglob("*"):
        if path.is_file():
            os.chmod(path, 0o666)

    index_path = library / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.is_file() else {}
    wanted: dict[str, list[tuple]] = {}
    for row in SELECTED:
        wanted.setdefault(row[0], []).append(row)

    backend = LtFileIPCBackend()
    full: dict[str, dict] = {}
    for path in sorted(work.rglob("*.dwg")):
        key = f"{path.parent.name}/{path.name}"
        await open_and_wait(backend, path)
        variables = await backend.drawing_get_variables(["INSUNITS"])
        units = int(variables.payload["INSUNITS"]) if variables.ok else 0
        blocks = await catalog_blocks(backend)
        full[key] = {"file": key, "insunits": units, "blocks": blocks}
        by_name = {block["name"]: block for block in blocks}
        for _, source_block, base_id, view, meaning in wanted.get(key, []):
            block = by_name.get(source_block)
            if block is None or "min" not in block:
                print(f"!! {key}: không thấy block hoặc không có kích thước: {source_block}")
                continue
            factor = MM_PER_UNIT.get(units)
            if factor is None:
                print(f"!! {key}: đơn vị chưa hỗ trợ ({units})")
                continue
            low = [block["min"][0] * factor, block["min"][1] * factor]
            high = [block["max"][0] * factor, block["max"][1] * factor]
            width, depth = round_mm(high[0] - low[0]), round_mm(high[1] - low[1])
            file_id = library_id(base_id, low, high)
            exported = (library / f"{file_id}.dwg").is_file()
            if not exported:
                result = await backend.block_export(source_block, file_id)
                if not result.ok:
                    print(f"!! {key}: {source_block}: {result.error}")
                    continue
            index[file_id] = {
                "source_file": key, "source_block": source_block, "view": view,
                "meaning": meaning, "units": UNIT_NAMES.get(units, units), "mm_per_unit": factor,
                "size_mm": [width, depth],
                "bbox_mm": [round(low[0], 1), round(low[1], 1), round(high[0], 1), round(high[1], 1)],
                "dynamic": key.startswith("Dynamic"),
            }
            print(("kept  " if exported else "wrote ") + file_id)
        index_path.write_text(json.dumps(index, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    if args.catalog_json:
        args.catalog_json.write_text(json.dumps(full, ensure_ascii=False, indent=1), encoding="utf-8")
    shutil.rmtree(work, ignore_errors=True)
    print(f"{len(index)} block trong thư viện; {sum(len(v['blocks']) for v in full.values())} block trong mẫu")


if __name__ == "__main__":
    asyncio.run(main())
