"""Run an explicit Beiming ensure_ready probe against one isolated session."""
import asyncio
import json
import sys

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def main():
    url = sys.argv[1]
    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as client:
            await client.initialize()
            result = await client.call_tool("system", {"operation": "ensure_ready"})
            for block in result.content:
                if getattr(block, "type", "") == "text":
                    print(block.text)
                    return
            print(json.dumps({"ok": not result.isError, "result": str(result)}))


if __name__ == "__main__":
    asyncio.run(main())
