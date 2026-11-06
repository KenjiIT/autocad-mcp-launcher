"""Write launcher/team_key.dat from the KNOWLEDGE_TEAM_KEY environment variable (CI only).

The file is gitignored: the key stays out of the public source and is added to the
release package at build time. The encoding only keeps the key from showing up in
a text search; anyone with the package can still recover it.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "launcher"))
import knowledge_propose  # noqa: E402


def main() -> int:
    key = os.environ.get("KNOWLEDGE_TEAM_KEY", "").strip()
    target = Path(knowledge_propose.__file__).with_name(knowledge_propose.EMBEDDED_KEY_FILE)
    if not key:
        print("KNOWLEDGE_TEAM_KEY is empty; building without an embedded team key.")
        target.unlink(missing_ok=True)
        return 0
    target.write_text(knowledge_propose.encode_key(key), encoding="ascii")
    print(f"Wrote {target.name} ({len(key)} characters encoded).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
