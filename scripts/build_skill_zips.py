"""Build one upload-ready zip per skill into dist/ (for Claude Desktop's Skills upload).

Run this after creating or changing any skill:

    python scripts/build_skill_zips.py                      # every skill
    python scripts/build_skill_zips.py NAME [NAME ...]      # only these
    python scripts/build_skill_zips.py --skip NAME          # all but these

The source is .claude/skills; .codex/skills and .agents/skills must match it, so the
script stops if they differ.  Each zip holds the whole skill folder under <name>/.
"""
import argparse
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / ".claude" / "skills"
MIRRORS = (ROOT / ".codex" / "skills", ROOT / ".agents" / "skills")


def files_of(skill_dir):
    return [f for f in sorted(skill_dir.rglob("*")) if f.is_file() and "__pycache__" not in f.parts]


def differs(name):
    """Mirror folders whose content differs from the .claude copy."""
    reference = {f.relative_to(SOURCE / name).as_posix(): f.read_bytes() for f in files_of(SOURCE / name)}
    bad = []
    for mirror in MIRRORS:
        folder = mirror / name
        found = {f.relative_to(folder).as_posix(): f.read_bytes() for f in files_of(folder)} if folder.is_dir() else None
        if found != reference:
            bad.append(str(mirror.parent.name))
    return bad


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("names", nargs="*", help="skills to build (default: all)")
    parser.add_argument("--skip", action="append", default=[], help="skill to leave out")
    args = parser.parse_args()

    available = sorted(p.name for p in SOURCE.iterdir() if (p / "SKILL.md").is_file())
    unknown = [n for n in args.names + args.skip if n not in available]
    if unknown:
        sys.exit(f"Unknown skill: {', '.join(unknown)}")
    names = [n for n in (args.names or available) if n not in args.skip]

    out = ROOT / "dist"
    out.mkdir(exist_ok=True)
    problems = {n: differs(n) for n in names}
    problems = {n: bad for n, bad in problems.items() if bad}
    if problems:
        for name, bad in problems.items():
            print(f"{name}: differs in {', '.join(bad)}", file=sys.stderr)
        sys.exit("Sync the three skill folders first, then build again.")

    for name in names:
        target = out / f"{name}.zip"
        with ZipFile(target, "w", compression=ZIP_DEFLATED) as archive:
            for file in files_of(SOURCE / name):
                archive.write(file, f"{name}/{file.relative_to(SOURCE / name).as_posix()}")
        print(f"{target.relative_to(ROOT).as_posix()}  {target.stat().st_size} bytes")


if __name__ == "__main__":
    main()
