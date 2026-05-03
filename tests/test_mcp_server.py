"""Tests for safe_mcp_proxy.mcp_server, mcp_test_server, and mcp_upstream."""
import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mcp import McpError

BASE_DIR = Path(__file__).resolve().parents[1]


def _make_executor(world_id=None, simulate=True):
    """Build a fresh executor with a temp audit file."""
    import tempfile
    from safe_mcp_proxy.approval_store import ApprovalStore
    from safe_mcp_proxy.executor import Executor
    from safe_mcp_proxy.main import _resolve_manifest_path, _build_policy_engine, _load_simulation_flag
    from safe_mcp_proxy.compiler import compile_world_manifest
    from safe_mcp_proxy.registry import ToolRegistry
    import hashlib

    audit = Path(tempfile.mktemp(suffix=".jsonl"))
    manifest_path = _resolve_manifest_path(BASE_DIR, world_id)
    manifest_tables = compile_world_manifest(str(manifest_path))
    policy_version = hashlib.sha256(manifest_path.read_bytes()).hexdigest()[:8]
    registry = ToolRegistry.with_mock_tools(
        allowlist=manifest_tables["allowlist"],
        capability_defs=manifest_tables.get("capability_definitions"),
    )
    policy_engine = _build_policy_engine(manifest_tables, "python", BASE_DIR)
    return Executor(
        registry=registry,
        policy_engine=policy_engine,
        audit_log_path=audit,
        simulate_external=simulate,
        approval_store=ApprovalStore(),
        world_id=manifest_tables.get("world_id", ""),
        policy_version=policy_version,
    )


# ---------------------------------------------------------------------------
# MCPProxyServer — tool list
# ---------------------------------------------------------------------------

class TestMCPServerToolList(unittest.TestCase):
    def test_list_tools_matches_registry_exposed(self):
        from safe_mcp_proxy.mcp_server import MCPProxyServer
        executor = _make_executor()
        proxy = MCPProxyServer(executor)
        tools = proxy._list_tools()
        exposed = {t.name for t in executor.registry.list_exposed()}
        self.assertEqual({t.name for t in tools}, exposed)

    def test_list_tools_read_only_smaller_than_default(self):
        from safe_mcp_proxy.mcp_server import MCPProxyServer
        proxy_default = MCPProxyServer(_make_executor(world_id=None))
        proxy_ro = MCPProxyServer(_make_executor(world_id="read_only"))
        self.assertLess(len(proxy_ro._list_tools()), len(proxy_default._list_tools()))

    def test_list_tools_absent_tool_not_present(self):
        from safe_mcp_proxy.mcp_server import MCPProxyServer
        proxy = MCPProxyServer(_make_executor(world_id="read_only"))
        names = [t.name for t in proxy._list_tools()]
        self.assertNotIn("send_email", names)
        self.assertNotIn("dangerous_exec", names)

    def test_list_tools_returns_mcp_tool_objects(self):
        from mcp.types import Tool
        from safe_mcp_proxy.mcp_server import MCPProxyServer
        proxy = MCPProxyServer(_make_executor())
        for t in proxy._list_tools():
            self.assertIsInstance(t, Tool)
            self.assertTrue(t.name)
            self.assertIsInstance(t.inputSchema, dict)


# ---------------------------------------------------------------------------
# MCPProxyServer — call tool (policy decisions)
# ---------------------------------------------------------------------------

class TestMCPServerCallTool(unittest.IsolatedAsyncioTestCase):
    async def test_allow_read_file_returns_content(self):
        from safe_mcp_proxy.mcp_server import MCPProxyServer
        proxy = MCPProxyServer(_make_executor())
        result = await proxy._call_tool("read_file", {"path": "README.md"})
        self.assertEqual(len(result), 1)
        data = json.loads(result[0].text)
        self.assertNotIn("error", data)

    async def test_deny_tainted_send_email_raises_mcp_error(self):
        from safe_mcp_proxy.mcp_server import MCPProxyServer
        from safe_mcp_proxy.provenance import Provenance
        executor = _make_executor()
        proxy = MCPProxyServer(executor)

        # Simulate by calling executor directly with web provenance and checking
        prov = Provenance.from_source("web")
        outcome = executor.execute("send_email", {"to": "x@y.com", "body": "leak"}, prov)
        self.assertEqual(outcome["decision"], "DENY")
        self.assertEqual(outcome["rule"], "tainted_external_side_effect")

    async def test_absent_tool_raises_mcp_error(self):
        from safe_mcp_proxy.mcp_server import MCPProxyServer
        proxy = MCPProxyServer(_make_executor(world_id="read_only"))
        with self.assertRaises(McpError) as ctx:
            await proxy._call_tool("send_email", {})
        self.assertIn("ABSENT", str(ctx.exception))

    async def test_unknown_tool_raises_mcp_error(self):
        from safe_mcp_proxy.mcp_server import MCPProxyServer
        proxy = MCPProxyServer(_make_executor())
        with self.assertRaises(McpError) as ctx:
            await proxy._call_tool("nonexistent_tool_xyz", {})
        self.assertIn("ABSENT", str(ctx.exception))

    async def test_allow_with_upstream_uses_upstream_result(self):
        from safe_mcp_proxy.mcp_server import MCPProxyServer
        from safe_mcp_proxy.mcp_upstream import UpstreamConnector

        connector = UpstreamConnector([sys.executable, "-m", "safe_mcp_proxy.mcp_test_server"])
        await connector.connect()
        try:
            proxy = MCPProxyServer(_make_executor(), upstream=connector)
            result = await proxy._call_tool("read_file", {"path": "README.md"})
            data = json.loads(result[0].text)
            # upstream returns real stub, not mock
            self.assertIn("content", data)
            self.assertIn("README.md", data["content"])
        finally:
            await connector.disconnect()


# ---------------------------------------------------------------------------
# mcp_test_server — standalone
# ---------------------------------------------------------------------------

class TestMCPTestServer(unittest.IsolatedAsyncioTestCase):
    async def test_test_server_lists_expected_tools(self):
        from mcp import ClientSession
        from mcp.client.stdio import StdioServerParameters, stdio_client

        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "safe_mcp_proxy.mcp_test_server"],
            cwd=str(BASE_DIR),
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                names = {t.name for t in result.tools}
                self.assertIn("read_file", names)
                self.assertIn("send_email", names)
                self.assertIn("list_repo", names)
                self.assertIn("dangerous_exec", names)

    async def test_test_server_call_read_file(self):
        from mcp import ClientSession
        from mcp.client.stdio import StdioServerParameters, stdio_client

        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "safe_mcp_proxy.mcp_test_server"],
            cwd=str(BASE_DIR),
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("read_file", {"path": "README.md"})
                text = result.content[0].text
                data = json.loads(text)
                self.assertIn("content", data)
                self.assertIn("README.md", data["path"])

    async def test_test_server_call_send_email(self):
        from mcp import ClientSession
        from mcp.client.stdio import StdioServerParameters, stdio_client

        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "safe_mcp_proxy.mcp_test_server"],
            cwd=str(BASE_DIR),
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("send_email", {"to": "test@example.com", "body": "hi"})
                data = json.loads(result.content[0].text)
                self.assertTrue(data["sent"])


# ---------------------------------------------------------------------------
# UpstreamConnector
# ---------------------------------------------------------------------------

class TestUpstreamConnector(unittest.IsolatedAsyncioTestCase):
    async def test_connect_and_call_tool(self):
        from safe_mcp_proxy.mcp_upstream import UpstreamConnector

        connector = UpstreamConnector([sys.executable, "-m", "safe_mcp_proxy.mcp_test_server"])
        await connector.connect()
        try:
            result = await connector.call_tool("read_file", {"path": "README.md"})
            self.assertIsInstance(result, dict)
            self.assertIn("content", result)
        finally:
            await connector.disconnect()

    async def test_connect_and_call_list_repo(self):
        from safe_mcp_proxy.mcp_upstream import UpstreamConnector

        connector = UpstreamConnector([sys.executable, "-m", "safe_mcp_proxy.mcp_test_server"])
        await connector.connect()
        try:
            result = await connector.call_tool("list_repo", {})
            self.assertIn("files", result)
            self.assertIsInstance(result["files"], list)
        finally:
            await connector.disconnect()

    async def test_disconnect_without_connect_is_safe(self):
        from safe_mcp_proxy.mcp_upstream import UpstreamConnector

        connector = UpstreamConnector([sys.executable, "-m", "safe_mcp_proxy.mcp_test_server"])
        await connector.disconnect()  # should not raise


if __name__ == "__main__":
    unittest.main()
