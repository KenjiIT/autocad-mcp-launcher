"""Start an isolated Beiming MCP server for one AutoCAD PID."""
import os
import sys
from pathlib import Path


def main():
    repo = Path(sys.argv[1]).resolve(strict=True)
    port = int(sys.argv[2])
    sys.path.insert(0, str(repo / "src"))
    sys.path.insert(0, str(Path(__file__).resolve().parent / "extensions"))
    os.chdir(repo)
    os.environ.setdefault("AUTOCAD_MCP_BACKEND", "file_ipc")
    os.environ.setdefault("AUTOCAD_MCP_AUTOSTART", "false")
    from beiming_timeout import apply as apply_read_timeout
    apply_read_timeout()
    from autocad_mcp.server import mcp
    from beiming_batch_copy import register as register_batch_copy
    from beiming_region_copy import register as register_region_copy
    from beiming_delete_batch import register as register_delete_batch
    register_batch_copy(mcp)
    register_region_copy(mcp)
    register_delete_batch(mcp)
    mcp.settings.host = "127.0.0.1"
    mcp.settings.port = port
    mcp.settings.stateless_http = True
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
