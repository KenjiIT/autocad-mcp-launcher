"""Build a ZIP that includes the launcher and its MCP source trees."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "dist" / "autocad-mcp-launcher-complete.zip"
PACKAGE_NAME = "autocad-mcp-launcher"
SKILL_ARCHIVES = (
    "autocad-agent-coordinator",
    "autocad-identify-and-measure",
    "autocad-start-construction-drawing",
    "autocad-verify-drawing-inputs",
)
INCLUDE = (
    "VERSION",
    "README.md",
    "Start AutoCAD MCP.cmd",
    "Start AutoCAD MCP.vbs",
    "start.ps1",
    "launcher",
    "lt-adapter",
    "blocks",
    "scripts",
    ".codex",
    ".claude",
    "dist/autocad-agent-coordinator.zip",
    "dist/autocad-identify-and-measure.zip",
    "dist/autocad-start-construction-drawing.zip",
    "dist/autocad-verify-drawing-inputs.zip",
    "puran-water-autocad-mcp",
    "autocad-beiming-mcp-custom",
)
SKIP_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "logs", "output", ".local-data", "bin", "obj"}
SKIP_SUFFIXES = {".dwg"}  # User drawings must not be bundled with the launcher.


def files_to_package():
    for entry in INCLUDE:
        path = ROOT / entry
        if not path.exists():
            raise FileNotFoundError(f"Missing package input: {path}")
        if path.is_file():
            yield path
            continue
        for candidate in sorted(path.rglob("*")):
            if candidate.is_file() and not candidate.is_symlink():
                relative = candidate.relative_to(ROOT)
                if not any(part in SKIP_DIRS for part in relative.parts) and candidate.suffix.lower() not in SKIP_SUFFIXES:
                    yield candidate


def main():
    for repo in ("puran-water-autocad-mcp", "autocad-beiming-mcp-custom"):
        if not (ROOT / repo / "pyproject.toml").is_file():
            raise RuntimeError(f"Missing {repo} source; initialize Git submodules first")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    for skill_name in SKILL_ARCHIVES:
        skill_dir = ROOT / ".codex" / "skills" / skill_name
        if not (skill_dir / "SKILL.md").is_file():
            raise FileNotFoundError(f"Missing skill: {skill_dir / 'SKILL.md'}")
        with ZipFile(ROOT / "dist" / f"{skill_name}.zip", "w", compression=ZIP_DEFLATED) as skill_archive:
            for file in sorted(skill_dir.rglob("*")):
                if file.is_file() and "__pycache__" not in file.parts:
                    skill_archive.write(file, f"{skill_name}/{file.relative_to(skill_dir).as_posix()}")
    with ZipFile(OUTPUT, "w", compression=ZIP_DEFLATED) as archive:
        for path in files_to_package():
            archive.write(path, f"{PACKAGE_NAME}/{path.relative_to(ROOT).as_posix()}")
    print(OUTPUT)


if __name__ == "__main__":
    main()
