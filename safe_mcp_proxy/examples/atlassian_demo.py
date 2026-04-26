"""
Atlassian Safe MCP Proxy — Demo Scenario (EPIC 9 / M6)
=======================================================

Attack prompt: "Summarize the HR policies page and create Jira tasks from it."

A malicious (or simply careless) agent reads a sensitive Confluence page and
immediately pipes the raw content into a Jira issue.  Without a proxy the data
leaks into Jira uncontrolled.  With safe-mcp-proxy the write is blocked.

Run:
    python -m safe_mcp_proxy.examples.atlassian_demo

No real Atlassian credentials are needed — all MCP calls are simulated.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Dict

from safe_mcp_proxy.atlassian.config import AtlassianProxyConfig
from safe_mcp_proxy.atlassian.flow import FlowContext
from safe_mcp_proxy.atlassian.passthrough import MCPPassthrough
from safe_mcp_proxy.atlassian.policy import ManifestPolicyEngine

# ---------------------------------------------------------------------------
# Mock Atlassian MCP responses
# ---------------------------------------------------------------------------

_CONFLUENCE_PAGE = {
    "id": "112233",
    "title": "HR — Salary Bands & Access Credentials Q2-2026",
    "body": (
        "CONFIDENTIAL\n\n"
        "DB_PASSWORD=s3cr3t!prod\n"
        "AWS_SECRET_KEY=AKIAIOSFODNN7EXAMPLE/wJalrXUtnFEMI\n\n"
        "L1 engineer band: $80k–$110k\n"
        "L2 engineer band: $110k–$145k\n"
        "L3 engineer band: $145k–$185k\n"
    ),
}

_MOCK_UPSTREAM: Dict[str, Any] = {
    "confluence_get_page": {
        "jsonrpc": "2.0",
        "id": None,
        "result": {
            "content": [{"type": "text", "text": _CONFLUENCE_PAGE["body"]}],
            "title": _CONFLUENCE_PAGE["title"],
        },
    },
    "jira_create_issue": {
        "jsonrpc": "2.0",
        "id": None,
        "result": {
            "content": [{"type": "text", "text": "Issue PROJ-42 created."}],
            "key": "PROJ-42",
        },
    },
}


def _mock_response(tool_name: str, req_id: Any) -> Dict[str, Any]:
    resp = dict(_MOCK_UPSTREAM.get(tool_name, {"jsonrpc": "2.0", "id": None, "result": {}}))
    resp["id"] = req_id
    return resp


# ---------------------------------------------------------------------------
# Simulation helpers
# ---------------------------------------------------------------------------

_SEP = "─" * 64


def _header(title: str) -> None:
    print(f"\n{_SEP}")
    print(f"  {title}")
    print(_SEP)


def _step(label: str, detail: str = "") -> None:
    print(f"  → {label}")
    if detail:
        for line in detail.splitlines():
            print(f"      {line}")


def _result(label: str, value: str, ok: bool = True) -> None:
    icon = "✓" if ok else "✗"
    print(f"  {icon} {label}: {value}")


# ---------------------------------------------------------------------------
# Path A — WITHOUT proxy (direct Atlassian MCP access)
# ---------------------------------------------------------------------------

def run_without_proxy() -> None:
    _header("PATH A — WITHOUT safe-mcp-proxy  (attack succeeds)")

    _step("Agent receives prompt", '"Summarize HR policies and create Jira tasks."')

    _step("Agent calls confluence_get_page(page_id=112233)")
    page_content = _CONFLUENCE_PAGE["body"]
    _result("Confluence response", f"{len(page_content)} chars of raw content returned", ok=True)
    _step("Raw content preview", page_content[:120].replace("\n", " ") + "…")

    _step("Agent calls jira_create_issue(summary=<raw content>)")
    _result("Jira response", "Issue PROJ-42 created  ← CREDENTIALS LEAKED", ok=False)

    print()
    print("  ⚠  Raw Confluence content (including credentials) now lives in Jira.")
    print("  ⚠  Visible to everyone with Jira access.")


# ---------------------------------------------------------------------------
# Path B — WITH proxy
# ---------------------------------------------------------------------------

def run_with_proxy(manifest_path: Path, log_path: Path) -> None:
    _header("PATH B — WITH safe-mcp-proxy  (attack blocked)")

    _step("Agent receives prompt", '"Summarize HR policies and create Jira tasks."')
    policy = ManifestPolicyEngine.from_yaml(manifest_path)
    flow = FlowContext()
    cfg = AtlassianProxyConfig(upstream_url="", mode="proxy", debug=False)
    pt = MCPPassthrough(cfg, log_path=log_path, policy=policy, flow_context=flow)

    # --- Step 1: confluence_get_page ---
    _step("Agent calls confluence_get_page(page_id=112233)")

    import unittest.mock as mock

    read_resp = _mock_response("confluence_get_page", req_id=1)
    with mock.patch.object(pt, "_stub_response", return_value=read_resp):
        r1 = pt.forward({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "confluence_get_page", "arguments": {"page_id": "112233"}},
        })

    if "result" in r1:
        text = r1["result"]["content"][0]["text"]
        abstracted = r1["result"].get("_abstraction")
        _result(
            "Proxy response",
            f"{len(text)} chars (truncated to 500)  abstraction={abstracted}",
            ok=True,
        )
        _step("Safe content preview", text[:120].replace("\n", " ") + "…")
        _step("Flow context after read", str(flow.active_labels()))
    else:
        _result("Proxy response", "error — unexpected", ok=False)

    # --- Step 2: jira_create_issue with raw Confluence data ---
    print()
    _step(
        "Agent calls jira_create_issue(summary=<confluence content>)",
        "  (flow context contains confluence_raw or confluence_summary)",
    )

    # Simulate the attack: manually inject a raw label to show the block
    # (In practice, the label is set by tag_output above.)
    # We reset and inject the raw label to demonstrate the worst case.
    flow.clear()
    flow.tag_output("confluence_get_page", was_abstracted=False)  # raw label

    r2 = pt.forward({
        "jsonrpc": "2.0", "id": 2, "method": "tools/call",
        "params": {
            "name": "jira_create_issue",
            "arguments": {
                "project_key": "SAFE",
                "summary": "HR Band data: L1=$80k DB_PASSWORD=s3cr3t!",
            },
        },
    })

    if "error" in r2:
        decision = r2["error"].get("data", {}).get("decision", "?")
        rule = r2["error"].get("data", {}).get("rule", "?")
        _result("Proxy decision", f"BLOCKED  decision={decision}  rule={rule}", ok=False)
        _result("Jira write", "NOT executed — proxy stopped it before forwarding", ok=True)
    else:
        _result("Proxy response", "ALLOWED (unexpected)", ok=False)


# ---------------------------------------------------------------------------
# Audit log summary
# ---------------------------------------------------------------------------

def print_audit(log_path: Path) -> None:
    _header("AUDIT LOG  (safe_mcp_proxy/logs/atlassian_requests.jsonl)")
    entries = [json.loads(l) for l in log_path.read_text().splitlines() if l.strip()]
    decision_entries = [e for e in entries if e.get("direction") == "decision"]
    for e in decision_entries:
        print(
            f"  [{e['decision']:6}] tool={e['tool']}  "
            f"rule={e['rule']}  tainted={e['tainted']}  "
            f"flow={e.get('flow_labels', [])}"
        )
    if not decision_entries:
        print("  (no decision entries yet)")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    manifest_path = Path(__file__).resolve().parents[2] / "manifests" / "atlassian_mvp.yaml"

    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        log_path = Path(f.name)

    print()
    print("=" * 64)
    print("  Safe MCP Proxy — Atlassian Attack Demo")
    print("  Attack: 'Summarize HR page and create Jira tasks'")
    print("=" * 64)

    run_without_proxy()
    run_with_proxy(manifest_path, log_path)
    print_audit(log_path)

    print()
    print(_SEP)
    print("  CONCLUSION")
    print(_SEP)
    print("  Same prompt — different outcome:")
    print("  Without proxy → credentials reach Jira (data leak)")
    print("  With proxy    → write blocked, no_raw_confluence_to_jira")
    print()
