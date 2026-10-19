"""Run one checkout as a local Streamable HTTP MCP server."""
import os
import sys
from pathlib import Path


def main():
    repo = Path(sys.argv[1]).resolve(strict=True)
    port = int(sys.argv[2])
    sys.path.insert(0, str(repo / "src"))
    os.chdir(repo)
    os.environ.setdefault("AUTOCAD_MCP_BACKEND", "file_ipc")
    if repo.name.startswith("beiming183"):
        os.environ.setdefault("AUTOCAD_MCP_OUTPUT_ROOT", str(repo / "output"))
        os.environ.setdefault("AUTOCAD_MCP_AUTOSTART", "false")
        from beiming_timeout import apply as apply_beiming_read_timeout
        apply_beiming_read_timeout()
    from autocad_mcp.server import mcp
    if repo.name.startswith("beiming183"):
        from beiming_batch_copy import register as register_batch_copy
        register_batch_copy(mcp)
        from beiming_region_copy import register as register_region_copy
        register_region_copy(mcp)
        from beiming_delete_batch import register as register_delete_batch
        register_delete_batch(mcp)
    mcp.settings.host = "127.0.0.1"
    mcp.settings.port = port
    mcp.settings.stateless_http = True
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
