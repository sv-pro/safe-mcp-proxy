from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from safe_mcp_proxy.mcp_upstream import UpstreamConnector
from safe_mcp_proxy.policy import JiraPolicy
from safe_mcp_proxy.proxy import SafeJiraProxy


class SafeProxyMCPServer:
    def __init__(self, proxy: SafeJiraProxy):
        self.proxy = proxy
        self.server = self._build_server()

    def _build_server(self) -> Server:
        server = Server("safe-proxy")

        @server.list_tools()
        async def _list_tools() -> list[types.Tool]:
            filtered = await self.proxy.list_tools()
            return [
                types.Tool(
                    name=t["name"],
                    description=t.get("description", t["name"]),
                    inputSchema=t.get("inputSchema", {"type": "object", "properties": {}}),
                )
                for t in filtered
            ]

        @server.call_tool()
        async def _call_tool(name: str, arguments: dict[str, Any]) -> list[types.ContentBlock]:
            result = await self.proxy.call_tool(name, arguments or {})
            return [types.TextContent(type="text", text=json.dumps(result))]

        return server

    async def run(self) -> None:
        async with stdio_server() as (read, write):
            await self.server.run(read, write, self.server.create_initialization_options())


async def _main(policy_path: Path, upstream_command: list[str]) -> None:
    policy = JiraPolicy.load(policy_path)
    upstream = UpstreamConnector(upstream_command)
    await upstream.connect()
    try:
        proxy = SafeJiraProxy(upstream, policy)
        await SafeProxyMCPServer(proxy).run()
    finally:
        await upstream.disconnect()


def main() -> None:
    parser = argparse.ArgumentParser(description="Safe MCP proxy server for Jira")
    parser.add_argument("--policy", default="safe_mcp_proxy/config/jira_policy.yaml")
    parser.add_argument(
        "--upstream",
        nargs="+",
        required=True,
        help="Upstream Jira MCP server command, e.g. python -m my_jira_mcp_server",
    )
    args = parser.parse_args()

    asyncio.run(_main(Path(args.policy), args.upstream))


if __name__ == "__main__":
    main()
