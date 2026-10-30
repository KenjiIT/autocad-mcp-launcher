"""Experimental: run the Revit MCP server (mcp-servers-for-revit) behind a local HTTP port.

That server only speaks stdio, so supergateway wraps it as streamable HTTP.  The
server talks to the Revit add-in over a socket on 127.0.0.1:8080; the add-in is
installed separately from the project's release zip.
"""
import json
import os
import shutil
from pathlib import Path

PORT = 8877
SERVER_PACKAGE = "mcp-server-for-revit@1.0.0"
GATEWAY_PACKAGE = "supergateway@4.2.1"
PLUGIN_PORT = 8080
RELEASES_URL = "https://github.com/mcp-servers-for-revit/mcp-servers-for-revit/releases"
URL = f"http://127.0.0.1:{PORT}/mcp"
SUPPORTED_REVIT = range(2020, 2027)  # the v1.0.0 release zips cover Revit 2020-2026


def find_npx():
    return shutil.which("npx.cmd") or shutil.which("npx")


def local_server():
    """Server installed in %LOCALAPPDATA%\revit-mcp-server (better-sqlite3 pinned to 12.x,
    which has prebuilt binaries for Node 24; the npx copy builds 11.x from source and fails)."""
    entry = (Path(os.environ.get("LOCALAPPDATA", "")) / "revit-mcp-server" / "node_modules"
             / "mcp-server-for-revit" / "build" / "index.js")
    node = shutil.which("node")
    return f'"{node}" "{entry}"' if node and entry.is_file() else None


def command(npx):
    return [npx, "-y", GATEWAY_PACKAGE,
            "--stdio", local_server() or f"cmd /c npx -y {SERVER_PACKAGE}",
            "--outputTransport", "streamableHttp",
            "--host", "127.0.0.1", "--port", str(PORT)]


def installed_revit_versions():
    """Revit years found under Program Files, newest last."""
    root = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Autodesk"
    years = []
    try:
        for path in root.iterdir():
            name = path.name
            if name.startswith("Revit 20") and name[6:].isdigit() and (path / "Revit.exe").is_file():
                years.append(int(name[6:]))
    except OSError:
        pass
    return sorted(years)


def addin_versions():
    """Revit years whose Addins folder already holds the mcp-servers-for-revit add-in."""
    root = Path(os.environ.get("APPDATA", "")) / "Autodesk" / "Revit" / "Addins"
    try:
        return sorted(int(p.name) for p in root.iterdir()
                      if p.name.isdigit() and (p / "mcp-servers-for-revit.addin").is_file())
    except OSError:
        return []


def readiness():
    """Plain-language checklist lines: (ok, text)."""
    lines = []
    npx = find_npx()
    lines.append((bool(npx), "Node.js (npx) có sẵn" if npx else "Chưa có Node.js 20+ (cần npx)"))
    revits = installed_revit_versions()
    if revits:
        newest = revits[-1]
        note = "" if newest in SUPPORTED_REVIT else f" (bản phát hành chỉ hỗ trợ đến Revit {SUPPORTED_REVIT[-1]})"
        lines.append((newest in SUPPORTED_REVIT, f"Revit tìm thấy: {', '.join(map(str, revits))}{note}"))
    else:
        lines.append((False, "Không tìm thấy Revit trong Program Files"))
    addins = addin_versions()
    lines.append((bool(addins), f"Add-in đã cài cho Revit {', '.join(map(str, addins))}" if addins
                  else "Chưa cài add-in vào Revit (tải zip theo đúng bản Revit ở trang Releases)"))
    return lines


def config_text():
    return "\n\n".join([
        "# Claude Code\nclaude mcp add --transport http revit " + URL,
        '# OpenAI Codex (config.toml)\n[mcp_servers.revit]\nurl = "' + URL + '"',
        "# Claude Desktop (stdio, không cần nút Bắt đầu)\n" + json.dumps({"mcpServers": {"revit": {
            "command": "cmd", "args": ["/c", "npx", "-y", SERVER_PACKAGE]}}}, indent=2),
    ])
