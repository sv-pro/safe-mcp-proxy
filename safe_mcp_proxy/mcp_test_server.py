"""
Minimal upstream MCP server used as a test backend for safe-mcp-proxy.

Exposes four tools that mirror the registry mock tools:
  read_file      — read side effect (safe)
  list_repo      — internal side effect (safe)
  send_email     — external side effect (unsafe, blocked by proxy)
  dangerous_exec — external side effect (unsafe, blocked by proxy)

Run standalone:
    python -m safe_mcp_proxy.mcp_test_server
"""
import asyncio
import json

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server


_server = Server("safe-mcp-test-upstream")

_TOOLS = [
    types.Tool(
        name="read_file",
        description="Read a file from the filesystem.",
        inputSchema={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
    ),
    types.Tool(
        name="list_repo",
        description="List repository contents.",
        inputSchema={"type": "object", "properties": {"path": {"type": "string"}}},
    ),
    types.Tool(
        name="send_email",
        description="Send an email to a recipient.",
        inputSchema={
            "type": "object",
            "properties": {"to": {"type": "string"}, "body": {"type": "string"}},
            "required": ["to", "body"],
        },
    ),
    types.Tool(
        name="dangerous_exec",
        description="Execute an arbitrary shell command.",
        inputSchema={"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]},
    ),
]


@_server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return _TOOLS


@_server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.ContentBlock]:
    if name == "read_file":
        path = (arguments or {}).get("path", "unknown")
        return [types.TextContent(type="text", text=json.dumps({"content": f"<contents of {path}>", "path": path}))]
    if name == "list_repo":
        return [types.TextContent(type="text", text=json.dumps({"files": ["README.md", "safe_mcp_proxy/", "tests/"]}))]
    if name == "send_email":
        to = (arguments or {}).get("to", "")
        return [types.TextContent(type="text", text=json.dumps({"sent": True, "to": to}))]
    if name == "dangerous_exec":
        cmd = (arguments or {}).get("command", "")
        return [types.TextContent(type="text", text=json.dumps({"stdout": f"<output of: {cmd}>", "exit_code": 0}))]
    raise ValueError(f"Unknown tool: {name}")


async def _main() -> None:
    async with stdio_server() as (read, write):
        await _server.run(read, write, _server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(_main())
