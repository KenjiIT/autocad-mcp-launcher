"""Claude Desktop stdio adapter for one gateway endpoint."""
import asyncio
import sys

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server


async def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("puran", "beiming"):
        raise SystemExit("Usage: stdio_bridge.py puran|beiming")
    name = sys.argv[1]
    async with streamablehttp_client(f"http://127.0.0.1:8764/{name}/mcp") as (read, write, _):
        async with ClientSession(read, write) as remote:
            remote_init = await remote.initialize()
            server = Server(f"autocad_{name}", instructions=remote_init.instructions)

            @server.list_tools()
            async def list_tools():
                return (await remote.list_tools()).tools

            @server.call_tool()
            async def call_tool(tool_name, arguments):
                result = await remote.call_tool(tool_name, arguments)
                return result.content

            @server.list_prompts()
            async def list_prompts():
                return (await remote.list_prompts()).prompts

            @server.get_prompt()
            async def get_prompt(prompt_name, arguments):
                return await remote.get_prompt(prompt_name, arguments)

            async with stdio_server() as (stdio_read, stdio_write):
                await server.run(
                    stdio_read, stdio_write, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
