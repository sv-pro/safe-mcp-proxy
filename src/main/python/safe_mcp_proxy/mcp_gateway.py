"""
Safe MCP Gateway — a governed stdio MCP server that fronts a *real* upstream MCP server.

This is the compose glue that turns the existing building blocks into one host-facing
entry point (see safe-mcp-proxy E16.1 / ai2rules D32). It wires together:

  - ManifestPolicyEngine (atlassian.policy) — ABSENT / arg_rules / taint decisions
  - UpstreamConnector    (mcp_upstream)     — real MCP client to the upstream server
  - an stdio JSON-RPC loop                  — the host-facing MCP server (Copilot / CC)

Pipeline:
  initialize  -> advertise this gateway
  tools/list  -> upstream's real tools, filtered to the manifest allowlist (ABSENT)
  tools/call  -> ManifestPolicyEngine.evaluate(); ALLOW -> forward upstream; else MCP error
  every decision is appended to an audit log (JSONL).

Usage:
  # local dry-run against the bundled test upstream
  python -m safe_mcp_proxy.mcp_gateway --manifest manifests/atlassian_mvp.yaml \\
      --upstream python -m safe_mcp_proxy.mcp_test_server

  # real Atlassian Remote MCP Server, bridged stdio<->SSE via mcp-remote
  python -m safe_mcp_proxy.mcp_gateway --manifest manifests/atlassian_mvp.yaml \\
      --upstream npx -y mcp-remote https://mcp.atlassian.com/v1/sse

Note: --upstream consumes the rest of the command line, so pass it LAST.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Set, Tuple

import yaml

from safe_mcp_proxy.atlassian.policy import ManifestPolicyEngine, PolicyDecision
from safe_mcp_proxy.provenance import TAINTED_CHANNELS

_SERVER_NAME = "safe-mcp-gateway"
_SERVER_VERSION = "0.1.0"
_PROTOCOL_VERSION = "2024-11-05"


class Upstream(Protocol):
    """The subset of UpstreamConnector the gateway depends on (also lets tests fake it)."""

    async def list_tools(self) -> List[Dict[str, Any]]: ...
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]: ...


def load_manifest(path: Path) -> Tuple[ManifestPolicyEngine, Set[str]]:
    """Load a world manifest into (policy engine, allowlist)."""
    with path.open(encoding="utf-8") as fh:
        manifest = yaml.safe_load(fh) or {}
    engine = ManifestPolicyEngine(manifest)
    allowlist: Set[str] = set(manifest.get("allowed_tools", []))
    return engine, allowlist


def _audit(audit_path: Optional[Path], entry: Dict[str, Any]) -> None:
    if audit_path is None:
        return
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    record = {"timestamp": datetime.now(timezone.utc).isoformat(), **entry}
    with audit_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


def _result(req_id: Any, result: Dict[str, Any]) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _error(req_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def _tool_error(req_id: Any, text: str) -> Dict[str, Any]:
    # MCP convention: tool-level failures come back as a result with isError=true,
    # not a JSON-RPC error — so the model sees the refusal as a tool outcome.
    return _result(req_id, {"isError": True, "content": [{"type": "text", "text": text}]})


async def handle_request(
    req: Dict[str, Any],
    *,
    engine: ManifestPolicyEngine,
    allowlist: Set[str],
    upstream: Upstream,
    source_channel: str = "cli",
    audit_path: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    """Handle one JSON-RPC request. Returns the response dict, or None for notifications."""
    method = req.get("method", "")
    req_id = req.get("id")

    if method == "notifications/initialized":
        return None

    if method == "initialize":
        return _result(req_id, {
            "protocolVersion": _PROTOCOL_VERSION,
            "serverInfo": {"name": _SERVER_NAME, "version": _SERVER_VERSION},
            "capabilities": {"tools": {}},
        })

    if method == "tools/list":
        tools = await upstream.list_tools()
        if allowlist:
            exposed = [t for t in tools if t.get("name") in allowlist]
        else:
            exposed = list(tools)
        absent = [t.get("name") for t in tools if t not in exposed]
        _audit(audit_path, {
            "event": "tools/list",
            "exposed": [t.get("name") for t in exposed],
            "absent": absent,
        })
        return _result(req_id, {"tools": exposed})

    if method == "tools/call":
        params = req.get("params") or {}
        name = params.get("name", "")
        arguments = params.get("arguments") or {}
        tainted = source_channel in TAINTED_CHANNELS
        decision: PolicyDecision = engine.evaluate(name, arguments, tainted, flow_context=None)
        _audit(audit_path, {
            "event": "tools/call",
            "tool": name,
            "decision": decision.decision,
            "rule": decision.rule,
            "tainted": tainted,
            "source": source_channel,
        })
        if decision.decision != "ALLOW":
            return _tool_error(req_id, f"{decision.decision}: {decision.rule}")
        try:
            result = await upstream.call_tool(name, arguments)
        except Exception as exc:  # upstream transport / tool failure
            return _tool_error(req_id, f"upstream error: {exc}")
        return _result(req_id, {"content": [{"type": "text", "text": json.dumps(result)}]})

    return _error(req_id, -32601, f"Method not found: {method}")


async def serve(
    *,
    engine: ManifestPolicyEngine,
    allowlist: Set[str],
    upstream: Upstream,
    source_channel: str = "cli",
    audit_path: Optional[Path] = None,
) -> None:
    """Drive the host-facing stdio JSON-RPC loop until EOF."""
    loop = asyncio.get_event_loop()
    while True:
        line = await loop.run_in_executor(None, sys.stdin.readline)
        if line == "":  # EOF — host closed the pipe
            break
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as exc:
            print(f"[mcp_gateway] malformed JSON: {exc}", file=sys.stderr, flush=True)
            continue
        resp = await handle_request(
            req,
            engine=engine,
            allowlist=allowlist,
            upstream=upstream,
            source_channel=source_channel,
            audit_path=audit_path,
        )
        if resp is not None:
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()


async def _amain(args: argparse.Namespace) -> None:
    from safe_mcp_proxy.mcp_upstream import UpstreamConnector  # lazy: needs the `mcp` SDK

    engine, allowlist = load_manifest(Path(args.manifest))
    audit_path = Path(args.audit) if args.audit else None
    connector = UpstreamConnector(args.upstream)
    await connector.connect()
    try:
        await serve(
            engine=engine,
            allowlist=allowlist,
            upstream=connector,
            source_channel=args.source,
            audit_path=audit_path,
        )
    finally:
        await connector.disconnect()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Safe MCP Gateway — governed stdio proxy over a real upstream MCP server",
    )
    parser.add_argument("--manifest", required=True, help="Path to the world manifest (Atlassian schema)")
    parser.add_argument("--source", default="cli", help="Provenance source channel (cli|web|email|tool_output)")
    parser.add_argument("--audit", default=None, help="Path to an append-only JSONL audit log")
    parser.add_argument(
        "--upstream",
        required=True,
        nargs=argparse.REMAINDER,
        help="Upstream MCP server command (pass LAST), e.g. "
        "--upstream npx -y mcp-remote https://mcp.atlassian.com/v1/sse",
    )
    args = parser.parse_args()
    if not args.upstream:
        parser.error("--upstream requires a command, e.g. --upstream python -m safe_mcp_proxy.mcp_test_server")
    asyncio.run(_amain(args))


if __name__ == "__main__":
    main()
