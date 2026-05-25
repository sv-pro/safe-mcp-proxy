"""Smoke tests for the Atlassian demo scenario (EPIC 9 / M6).

Verifies that the core attack-and-block sequence runs correctly without
needing real Atlassian credentials.
"""
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from safe_mcp_proxy.atlassian.config import AtlassianProxyConfig
from safe_mcp_proxy.atlassian.flow import FlowContext, LABEL_CONFLUENCE_RAW
from safe_mcp_proxy.atlassian.passthrough import MCPPassthrough
from safe_mcp_proxy.atlassian.policy import ManifestPolicyEngine

_MANIFEST_PATH = Path(__file__).resolve().parents[1] / "manifests" / "atlassian_mvp.yaml"

_CONFLUENCE_RESPONSE = {
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
        "content": [{"type": "text", "text": "CONFIDENTIAL\nDB_PASSWORD=s3cr3t!prod\n" * 20}],
        "title": "HR Policies",
    },
}


class TestAtlassianDemoScenario(unittest.TestCase):
    """End-to-end smoke test of the attack scenario used in the demo."""

    def _make_proxy(self, log_path=None):
        cfg = AtlassianProxyConfig(upstream_url="", mode="proxy")
        policy = ManifestPolicyEngine.from_yaml(_MANIFEST_PATH)
        flow = FlowContext()
        return MCPPassthrough(cfg, log_path=log_path, policy=policy, flow_context=flow), flow

    # ------------------------------------------------------------------

    def test_confluence_read_succeeds_and_is_abstracted(self):
        pt, flow = self._make_proxy()
        with patch.object(pt, "_stub_response", return_value=_CONFLUENCE_RESPONSE):
            resp = pt.forward({
                "jsonrpc": "2.0", "id": 1, "method": "tools/call",
                "params": {"name": "confluence_get_page", "arguments": {"page_id": "1"}},
            })
        self.assertNotIn("error", resp)
        text = resp["result"]["content"][0]["text"]
        self.assertLessEqual(len(text), 510, "Content should be truncated by safe abstraction")
        self.assertEqual(resp["result"].get("_abstraction"), "confluence_get_page_summary")

    def test_jira_write_blocked_after_raw_confluence_read(self):
        pt, flow = self._make_proxy()
        # Inject raw label (simulating read without abstraction)
        flow.tag_output("confluence_get_page", was_abstracted=False)

        resp = pt.forward({
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {
                "name": "jira_create_issue",
                "arguments": {"project_key": "SAFE", "summary": "leaked data"},
            },
        })
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["data"]["decision"], "DENY")
        self.assertEqual(resp["error"]["data"]["rule"], "no_raw_confluence_to_jira")

    def test_jira_write_allowed_when_no_confluence_read(self):
        pt, _ = self._make_proxy()
        resp = pt.forward({
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {
                "name": "jira_create_issue",
                "arguments": {"project_key": "SAFE", "summary": "normal task"},
            },
        })
        # No flow label → policy allows (stub returns isError because no upstream)
        self.assertNotIn("error", resp)

    def test_composite_tool_is_absent(self):
        pt, _ = self._make_proxy()
        resp = pt.forward({
            "jsonrpc": "2.0", "id": 4, "method": "tools/call",
            "params": {"name": "jira_bulk_create_issues", "arguments": {}},
        })
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["data"]["decision"], "ABSENT")

    def test_audit_log_records_allow_then_deny(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "log.jsonl"
            pt, flow = self._make_proxy(log_path=log_path)

            # Step 1: read
            with patch.object(pt, "_stub_response", return_value=_CONFLUENCE_RESPONSE):
                pt.forward({
                    "jsonrpc": "2.0", "id": 1, "method": "tools/call",
                    "params": {"name": "confluence_get_page", "arguments": {"page_id": "1"}},
                })

            # Inject raw label then write
            flow.clear()
            flow.tag_output("confluence_get_page", was_abstracted=False)
            pt.forward({
                "jsonrpc": "2.0", "id": 2, "method": "tools/call",
                "params": {
                    "name": "jira_create_issue",
                    "arguments": {"project_key": "SAFE", "summary": "leaked"},
                },
            })

            entries = [json.loads(l) for l in log_path.read_text().splitlines()]
            decisions = [e for e in entries if e.get("direction") == "decision"]

        self.assertEqual(len(decisions), 2)
        self.assertEqual(decisions[0]["decision"], "ALLOW")
        self.assertEqual(decisions[0]["tool"], "confluence_get_page")
        self.assertEqual(decisions[1]["decision"], "DENY")
        self.assertEqual(decisions[1]["rule"], "no_raw_confluence_to_jira")

    def test_demo_script_runs_without_error(self):
        """Full demo script produces output and exits cleanly."""
        captured = io.StringIO()
        with patch("sys.stdout", captured):
            from safe_mcp_proxy.examples import atlassian_demo
            import importlib
            # Re-run the module's main block via the functions directly
            with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
                log_path = Path(f.name)
            atlassian_demo.run_without_proxy()
            atlassian_demo.run_with_proxy(_MANIFEST_PATH, log_path)

        output = captured.getvalue()
        self.assertIn("BLOCKED", output)
        self.assertIn("no_raw_confluence_to_jira", output)
        self.assertIn("CREDENTIALS LEAKED", output)


if __name__ == "__main__":
    unittest.main()
