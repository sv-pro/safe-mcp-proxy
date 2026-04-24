"""Offline bundle replayer — replay policy decisions from a saved demo bundle.

Usage:
    python -m safe_mcp_proxy.bundle_replay path/to/bundle.json
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict

from safe_mcp_proxy.executor import Executor
from safe_mcp_proxy.policy_engine import PolicyEngine
from safe_mcp_proxy.registry import ToolRegistry


def replay_bundle(bundle: Dict[str, Any]) -> Dict[str, Any]:
    manifest = bundle["manifest"]
    registry = ToolRegistry.with_mock_tools(allowlist=manifest["allowlist"])
    policy_engine = PolicyEngine(
        allowlist=manifest["allowlist"],
        capability_map=manifest["capability_map"],
    )
    executor = Executor(
        registry=registry,
        policy_engine=policy_engine,
        audit_log_path=os.devnull,
        simulate_external=False,
    )

    results = []
    for trace in bundle.get("traces", []):
        audit_entry = {
            "tool": trace["tool_requested"],
            "taint": trace["taint"],
            "decision": trace["decision"],
            "rule": trace["rule_hit"],
        }
        result = executor.replay(audit_entry)
        results.append({"trace_id": trace["id"], **result})

    total = len(results)
    matched = sum(1 for r in results if r["matches"])
    return {"total": total, "matched": matched, "diverged": total - matched, "results": results}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m safe_mcp_proxy.bundle_replay <bundle.json>", file=sys.stderr)
        sys.exit(1)
    with open(sys.argv[1], encoding="utf-8") as fh:
        bundle = json.load(fh)
    summary = replay_bundle(bundle)
    print(json.dumps(summary, indent=2))
