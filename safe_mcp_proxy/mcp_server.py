"""
Safe MCP Proxy — policy-enforced MCP server for Claude Code and VS Code.

Every tool call from the MCP client is routed through the executor's
policy pipeline before being forwarded to the upstream MCP server.

Decision mapping:
  ALLOW  → forward to upstream (or return mock result if no upstream)
  DENY   → MCP error with rule name
  ABSENT → MCP error ("tool does not exist in this world")
  ASK    → MCP error with approval token (INTERACTIVE) or DENY (BACKGROUND)

Usage:
    python -m safe_mcp_proxy.mcp_server [--world WORLD_ID] [--upstream CMD...] [--mode interactive|background]
"""
import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

import mcp.types as types
from mcp import McpError
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import INTERNAL_ERROR, ErrorData

from safe_mcp_proxy.execution_mode import ExecutionMode
from safe_mcp_proxy.executor import Executor
from safe_mcp_proxy.main import build_executor
from safe_mcp_proxy.mcp_upstream import UpstreamConnector
from safe_mcp_proxy.provenance import Provenance

_BASE_DIR = Path(__file__).resolve().parents[1]


class MCPProxyServer:
    """Policy-enforced MCP proxy server.

    Wraps an Executor and optionally an UpstreamConnector.  The MCP SDK
    Server instance is built once; list_tools and call_tool handlers delegate
    to the public _list_tools / _call_tool methods so they are directly
    testable without running the stdio transport.
    """

    def __init__(
        self,
        executor: Executor,
        upstream: UpstreamConnector | None = None,
        execution_mode: ExecutionMode = ExecutionMode.INTERACTIVE,
    ):
        self.executor = executor
        self.upstream = upstream
        self.execution_mode = execution_mode
        self._server = self._build_sdk_server()

    # ------------------------------------------------------------------
    # Public, directly testable handlers
    # ------------------------------------------------------------------

    def _list_tools(self) -> list[types.Tool]:
        return [
            types.Tool(
                name=t.name,
                description=t.schema.get("description", t.name),
                inputSchema=t.schema,
            )
            for t in self.executor.registry.list_exposed()
        ]

    async def _call_tool(self, name: str, arguments: dict[str, Any]) -> list[types.ContentBlock]:
        provenance = Provenance.from_source("cli", execution_mode=self.execution_mode)
        outcome = self.executor.execute(name, arguments or {}, provenance)
        decision = outcome["decision"]
        rule = outcome["rule"]

        if decision == "ALLOW":
            if self.upstream is not None:
                raw = await self.upstream.call_tool(name, arguments or {})
            else:
                raw = outcome["result"]
            return [types.TextContent(type="text", text=json.dumps(raw))]

        raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"{decision}: {rule}"))

    # ------------------------------------------------------------------
    # Transport
    # ------------------------------------------------------------------

    def _build_sdk_server(self) -> Server:
        server = Server("safe-mcp-proxy")

        @server.list_tools()
        async def _handle_list_tools() -> list[types.Tool]:
            return self._list_tools()

        @server.call_tool()
        async def _handle_call_tool(name: str, arguments: dict) -> list[types.ContentBlock]:
            return await self._call_tool(name, arguments)

        return server

    async def run_stdio(self) -> None:
        async with stdio_server() as (read, write):
            await self._server.run(read, write, self._server.create_initialization_options())


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------

async def _run(world_id: str | None, upstream_cmd: list[str] | None, execution_mode: ExecutionMode) -> None:
    executor = build_executor(_BASE_DIR, world_id=world_id)

    upstream: UpstreamConnector | None = None
    if upstream_cmd:
        upstream = UpstreamConnector(upstream_cmd)
        await upstream.connect()

    try:
        server = MCPProxyServer(executor, upstream=upstream, execution_mode=execution_mode)
        await server.run_stdio()
    finally:
        if upstream:
            await upstream.disconnect()


def main() -> None:
    parser = argparse.ArgumentParser(description="Safe MCP Proxy — policy-enforced MCP server")
    parser.add_argument("--world", default=None, help="World ID (e.g. default, read_only, gemini_demo)")
    parser.add_argument(
        "--upstream", nargs="+", default=None,
        help="Command to spawn upstream MCP server (e.g. python -m safe_mcp_proxy.mcp_test_server)",
    )
    parser.add_argument("--mode", choices=["interactive", "background"], default="interactive")
    args = parser.parse_args()

    execution_mode = ExecutionMode.INTERACTIVE if args.mode == "interactive" else ExecutionMode.BACKGROUND
    asyncio.run(_run(args.world, args.upstream, execution_mode))


if __name__ == "__main__":
    main()
