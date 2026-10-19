"""Claude Desktop stdio adapter for an arbitrary streamable-HTTP MCP endpoint.

Usage: stdio_bridge_url.py <server_name> <http://host:port/mcp>
"""
import asyncio
import sys

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server


async def main():
    if len(sys.argv) != 3 or not sys.argv[2].startswith(("http://127.0.0.1", "http://localhost")):
        raise SystemExit("Usage: stdio_bridge_url.py <server_name> <http://127.0.0.1:PORT/mcp>")
    name, url = sys.argv[1], sys.argv[2]
    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as remote:
            await remote.initialize()
            server = Server(name)

            @server.list_tools()
            async def list_tools():
                return (await remote.list_tools()).tools

            @server.call_tool()
            async def call_tool(tool_name, arguments):
                result = await remote.call_tool(tool_name, arguments)
                return result.content

            async with stdio_server() as (stdio_read, stdio_write):
                await server.run(
                    stdio_read, stdio_write, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
