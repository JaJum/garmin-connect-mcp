"""Verify the M1 server over a real MCP stdio session."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


async def main() -> None:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        f"{SRC}{os.pathsep}{existing_pythonpath}"
        if existing_pythonpath
        else str(SRC)
    )
    env["GARMIN_MCP_MOCK"] = "true"
    env["PYTHONIOENCODING"] = "utf-8"

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "garmin_connect_mcp"],
        env=env,
        cwd=ROOT,
        encoding="utf-8",
    )

    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            init_result = await session.initialize()
            tools_result = await session.list_tools()
            names = [tool.name for tool in tools_result.tools]
            call_result = await session.call_tool("get_profile", {})

            text = (
                call_result.content[0].text
                if call_result.content
                and hasattr(call_result.content[0], "text")
                else ""
            )

            print(f"initialize={bool(init_result)}")
            print(f"tool_count={len(names)}")
            print(f"tool_names={names}")
            print(f"call_text={text}")


if __name__ == "__main__":
    asyncio.run(main())
