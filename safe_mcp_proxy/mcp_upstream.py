"""
UpstreamConnector — MCP client that forwards tool calls to an upstream MCP server.

Usage:
    connector = UpstreamConnector(["python", "-m", "safe_mcp_proxy.mcp_test_server"])
    await connector.connect()
    result = await connector.call_tool("read_file", {"path": "README.md"})
    await connector.disconnect()
"""
import json
import sys
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


class UpstreamConnector:
    def __init__(self, command: list[str]):
        self._command = command
        self._session: ClientSession | None = None
        self._stack: AsyncExitStack | None = None

    async def connect(self) -> None:
        params = StdioServerParameters(
            command=self._command[0],
            args=self._command[1:],
        )
        self._stack = AsyncExitStack()
        read, write = await self._stack.enter_async_context(
            stdio_client(params, errlog=open("/dev/null", "w"))
        )
        self._session = await self._stack.enter_async_context(ClientSession(read, write))
        await self._session.initialize()

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if self._session is None:
            raise RuntimeError("UpstreamConnector not connected — call connect() first")
        result = await self._session.call_tool(name, arguments)
        for block in result.content or []:
            if hasattr(block, "text"):
                try:
                    return json.loads(block.text)
                except (json.JSONDecodeError, ValueError):
                    return {"text": block.text}
        return {}

    async def disconnect(self) -> None:
        if self._stack is not None:
            await self._stack.aclose()
            self._stack = None
            self._session = None
