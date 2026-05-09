"""
Safe MCP Proxy — stdio JSON-RPC transport for Claude Code.

Handles MCP protocol (JSON-RPC 2.0 over stdio) without any external SDK.
Every tool call is routed through the executor policy pipeline before execution.

Decision mapping:
  ALLOW  → {"content": [{"type": "text", "text": "<json result>"}]}
  DENY   → {"isError": true, "content": [{"type": "text", "text": "<decision: rule>"}]}
  ABSENT → {"isError": true, "content": [{"type": "text", "text": "<decision: rule>"}]}
  ASK    → {"isError": true, "content": [{"type": "text", "text": "ASK: <rule>"}]}

Usage:
    python -m safe_mcp_proxy.mcp_server [--world WORLD_ID] [--mode interactive|background]
"""
import argparse
import json
import sys
from pathlib import Path

from safe_mcp_proxy.execution_mode import ExecutionMode
from safe_mcp_proxy.main import build_executor
from safe_mcp_proxy.provenance import Provenance

_BASE_DIR = Path(__file__).resolve().parents[1]
_SERVER_NAME = "safe-mcp-proxy"
_SERVER_VERSION = "0.1.0"


def _write(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def _respond(req_id, result: dict) -> None:
    _write({"jsonrpc": "2.0", "id": req_id, "result": result})


def _error(req_id, code: int, message: str) -> None:
    _write({"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}})


def run_stdio_server(
    world_id: str | None = None,
    execution_mode: ExecutionMode = ExecutionMode.INTERACTIVE,
) -> None:
    executor = build_executor(_BASE_DIR, world_id=world_id)

    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue

        try:
            req = json.loads(raw)
        except json.JSONDecodeError as exc:
            print(f"[mcp_server] malformed JSON: {exc}", file=sys.stderr, flush=True)
            continue

        req_id = req.get("id")
        method = req.get("method", "")
        params = req.get("params") or {}

        if method == "notifications/initialized":
            # Notification — no response expected
            continue

        elif method == "initialize":
            _respond(req_id, {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": _SERVER_NAME, "version": _SERVER_VERSION},
                "capabilities": {"tools": {}},
            })

        elif method == "tools/list":
            tools = [
                {
                    "name": t.name,
                    "description": t.schema.get("description", t.name),
                    "inputSchema": t.schema,
                }
                for t in executor.registry.list_exposed()
            ]
            _respond(req_id, {"tools": tools})

        elif method == "tools/call":
            name = params.get("name", "")
            arguments = params.get("arguments") or {}
            provenance = Provenance.from_source("cli", execution_mode=execution_mode)
            outcome = executor.execute(name, arguments, provenance)
            decision = outcome["decision"]
            rule = outcome["rule"]

            if decision == "ALLOW":
                _respond(req_id, {
                    "content": [{"type": "text", "text": json.dumps(outcome.get("result", {}))}],
                })
            else:
                _respond(req_id, {
                    "isError": True,
                    "content": [{"type": "text", "text": f"{decision}: {rule}"}],
                })

        else:
            _error(req_id, -32601, f"Method not found: {method}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Safe MCP Proxy — stdio JSON-RPC transport")
    parser.add_argument("--world", default=None, help="World ID (e.g. read_only, gemini_demo)")
    parser.add_argument("--mode", choices=["interactive", "background"], default="interactive")
    args = parser.parse_args()
    mode = ExecutionMode.INTERACTIVE if args.mode == "interactive" else ExecutionMode.BACKGROUND
    run_stdio_server(world_id=args.world, execution_mode=mode)


if __name__ == "__main__":
    main()
