"""Build a ZIP that includes the launcher and both upstream MCP source trees."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "dist" / "autocad-mcp-launcher-complete.zip"
PACKAGE_NAME = "autocad-mcp-launcher"
INCLUDE = (
    "README.md",
    "Start AutoCAD MCP.cmd",
    "Start AutoCAD MCP.vbs",
    "start.ps1",
    "launcher",
    "scripts",
    ".codex",
    ".claude",
    "dist/autocad-agent-coordinator.zip",
    "puran-water-autocad-mcp",
    "beiming183-cloud-AutoCAD-MCP",
)
SKIP_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "logs", "output"}


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
                if not any(part in SKIP_DIRS for part in relative.parts):
                    yield candidate


def main():
    for repo in ("puran-water-autocad-mcp", "beiming183-cloud-AutoCAD-MCP"):
        if not (ROOT / repo / "pyproject.toml").is_file():
            raise RuntimeError(f"Missing {repo} source; initialize Git submodules first")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(OUTPUT, "w", compression=ZIP_DEFLATED) as archive:
        for path in files_to_package():
            archive.write(path, f"{PACKAGE_NAME}/{path.relative_to(ROOT).as_posix()}")
    print(OUTPUT)


if __name__ == "__main__":
    main()
