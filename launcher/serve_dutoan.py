"""Run the dutoan MCP as a local Streamable HTTP server.

Unlike the CAD servers, dutoan has no AutoCAD session to protect, so it runs
stateless and the gateway keeps one copy alive for every agent.
"""
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path


def build_app(repo):
    sys.path.insert(0, str(repo / "src"))
    from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
    from starlette.applications import Starlette
    from starlette.routing import Route

    from dutoan_mcp.database import ensure_schema
    from dutoan_mcp.server import server

    ensure_schema()
    manager = StreamableHTTPSessionManager(app=server, stateless=True, json_response=True)

    class Endpoint:
        async def __call__(self, scope, receive, send):
            await manager.handle_request(scope, receive, send)

    @asynccontextmanager
    async def lifespan(_app):
        async with manager.run():
            yield

    return Starlette(routes=[Route("/mcp", endpoint=Endpoint())], lifespan=lifespan)


def main():
    import uvicorn

    repo = Path(sys.argv[1]).resolve(strict=True)
    port = int(sys.argv[2])
    os.chdir(repo)
    uvicorn.run(build_app(repo), host="127.0.0.1", port=port, log_level="warning", access_log=False)


if __name__ == "__main__":
    main()
