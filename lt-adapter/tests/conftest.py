from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
for source_root in (
    ROOT / "autocad-beiming-mcp-custom" / "src",
    ROOT / "lt-adapter" / "py",
):
    sys.path.insert(0, str(source_root))
