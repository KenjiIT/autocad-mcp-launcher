"""Experimental: run Demolinator/revit-mcp-server (Python, pyRevit Routes) behind a local HTTP port.

This is a different server from ``revit_mcp`` (mcp-servers-for-revit).  It talks to Revit through
pyRevit's Routes API on 127.0.0.1:48884, so pyRevit with Routes Server enabled must be installed
and Revit must be open.  The launcher starts it with ``uv run main.py --http`` from a local clone.
"""
import json
import os
import shutil
from pathlib import Path

import revit_mcp

PORT = 8000  # default of `main.py --http`; the endpoint is /mcp
ROUTES_PORT = 48884
REPO_URL = "https://github.com/Demolinator/revit-mcp-server"
URL = f"http://127.0.0.1:{PORT}/mcp"
SUPPORTED_REVIT = range(2024, 2028)


def find_uv():
    found = shutil.which("uv.exe") or shutil.which("uv")
    if found:
        return found
    # A launcher started before uv was installed has a stale PATH; check the usual install spots.
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    home = Path.home()
    candidates = [local / "Microsoft" / "WinGet" / "Links" / "uv.exe", home / ".local" / "bin" / "uv.exe"]
    candidates += sorted((local / "Microsoft" / "WinGet" / "Packages").glob("astral-sh.uv_*/uv.exe"))
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None


def repo_dir():
    """Local clone; override with the REVIT_PYREVIT_MCP_DIR environment variable."""
    custom = os.environ.get("REVIT_PYREVIT_MCP_DIR")
    if custom:
        return Path(custom)
    return Path(os.environ.get("LOCALAPPDATA", "")) / "revit-mcp-server-pyrevit"


def entry():
    path = repo_dir() / "main.py"
    return path if path.is_file() else None


def command(uv):
    return [uv, "run", "main.py", "--http"]


def readiness():
    """Plain-language checklist lines: (ok, text)."""
    lines = []
    uv = find_uv()
    lines.append((bool(uv), "uv có sẵn" if uv else "Chưa có uv (cài từ docs.astral.sh/uv)"))
    lines.append((entry() is not None,
                  f"Mã nguồn có ở {repo_dir()}" if entry()
                  else f"Chưa có mã nguồn: clone {REPO_URL} vào {repo_dir()} rồi chạy uv sync"))
    revits = revit_mcp.installed_revit_versions()
    if revits:
        newest = revits[-1]
        note = "" if newest in SUPPORTED_REVIT else f" (máy chủ này hỗ trợ Revit {SUPPORTED_REVIT[0]}–{SUPPORTED_REVIT[-1]})"
        lines.append((newest in SUPPORTED_REVIT, f"Revit tìm thấy: {', '.join(map(str, revits))}{note}"))
    else:
        lines.append((False, "Không tìm thấy Revit trong Program Files"))
    return lines


def config_text():
    return "\n\n".join([
        "# Claude Code\nclaude mcp add --transport http revit-pyrevit " + URL,
        '# OpenAI Codex (config.toml)\n[mcp_servers.revit_pyrevit]\nurl = "' + URL + '"',
        "# Claude Desktop (stdio, không cần nút Bật)\n" + json.dumps({"mcpServers": {"revit-pyrevit": {
            "command": "uv", "args": ["--directory", str(repo_dir()), "run", "main.py"]}}}, indent=2),
    ])
