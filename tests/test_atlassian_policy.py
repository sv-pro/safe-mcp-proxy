import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from safe_mcp_proxy.atlassian.config import AtlassianProxyConfig
from safe_mcp_proxy.atlassian.passthrough import MCPPassthrough
from safe_mcp_proxy.atlassian.policy import ManifestPolicyEngine, PolicyDecision

# Minimal manifest used across tests
_MANIFEST = {
    "world_id": "test_world",
    "allowed_tools": ["jira_read_issue", "jira_create_issue"],
    "external_write_tools": ["jira_create_issue"],
    "arg_rules": {
        "jira_create_issue": [
            {
                "arg": "project_key",
                "allowed_values": ["SAFE", "TEST"],
                "rule": "jira_create_restricted_projects",
            }
        ]
    },
    "flow_rules": {"tainted_source_blocks_external_write": True},
}


# ---------------------------------------------------------------------------
# ManifestPolicyEngine unit tests
# ---------------------------------------------------------------------------


class TestManifestPolicyEngine(unittest.TestCase):
    def _engine(self, manifest=None):
        return ManifestPolicyEngine(manifest or _MANIFEST)

    # --- ABSENT decisions ---

    def test_absent_when_tool_not_in_allowlist(self):
        d = self._engine().evaluate("jira_bulk_delete", {}, tainted=False)
        self.assertEqual(d.decision, "ABSENT")
        self.assertEqual(d.rule, "tool_not_allowlisted")
        self.assertEqual(d.tool, "jira_bulk_delete")

    def test_passthrough_mode_when_allowlist_empty(self):
        engine = ManifestPolicyEngine({})
        d = engine.evaluate("anything", {}, tainted=False)
        self.assertEqual(d.decision, "ALLOW")

    # --- DENY: flow rule ---

    def test_deny_tainted_source_external_write(self):
        d = self._engine().evaluate("jira_create_issue", {"project_key": "SAFE"}, tainted=True)
        self.assertEqual(d.decision, "DENY")
        self.assertEqual(d.rule, "tainted_source_blocks_external_write")

    def test_allow_read_tool_even_if_tainted(self):
        d = self._engine().evaluate("jira_read_issue", {}, tainted=True)
        self.assertEqual(d.decision, "ALLOW")

    def test_flow_rule_disabled_allows_tainted_external_write(self):
        manifest = {**_MANIFEST, "flow_rules": {"tainted_source_blocks_external_write": False}}
        d = ManifestPolicyEngine(manifest).evaluate(
            "jira_create_issue", {"project_key": "SAFE"}, tainted=True
        )
        self.assertEqual(d.decision, "ALLOW")

    # --- DENY: argument rules ---

    def test_deny_arg_rule_disallowed_value(self):
        d = self._engine().evaluate(
            "jira_create_issue", {"project_key": "PROD"}, tainted=False
        )
        self.assertEqual(d.decision, "DENY")
        self.assertEqual(d.rule, "jira_create_restricted_projects")

    def test_allow_arg_rule_allowed_value(self):
        d = self._engine().evaluate(
            "jira_create_issue", {"project_key": "SAFE"}, tainted=False
        )
        self.assertEqual(d.decision, "ALLOW")

    def test_deny_arg_rule_missing_arg(self):
        # Missing arg → value is None, not in allowed_values → DENY
        d = self._engine().evaluate("jira_create_issue", {}, tainted=False)
        self.assertEqual(d.decision, "DENY")

    def test_no_arg_rules_for_tool_allows(self):
        d = self._engine().evaluate("jira_read_issue", {"issue_key": "PROJ-1"}, tainted=False)
        self.assertEqual(d.decision, "ALLOW")

    # --- ALLOW default ---

    def test_allow_default(self):
        d = self._engine().evaluate(
            "jira_create_issue", {"project_key": "TEST"}, tainted=False
        )
        self.assertEqual(d.decision, "ALLOW")
        self.assertEqual(d.rule, "default_allow")

    # --- PolicyDecision is frozen ---

    def test_policy_decision_frozen(self):
        d = PolicyDecision("ALLOW", "default_allow", "tool", False)
        with self.assertRaises(Exception):
            d.decision = "DENY"  # type: ignore[misc]

    # --- from_yaml ---

    def test_from_yaml_loads_manifest(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            import yaml
            yaml.dump(_MANIFEST, f)
            path = Path(f.name)
        try:
            engine = ManifestPolicyEngine.from_yaml(path)
            d = engine.evaluate("jira_bulk_delete", {}, tainted=False)
            self.assertEqual(d.decision, "ABSENT")
        finally:
            path.unlink()

    def test_from_yaml_loads_real_atlassian_manifest(self):
        manifest_path = Path(__file__).resolve().parents[1] / "manifests" / "atlassian_mvp.yaml"
        engine = ManifestPolicyEngine.from_yaml(manifest_path)
        self.assertEqual(
            engine.evaluate("jira_read_issue", {}, tainted=False).decision, "ALLOW"
        )
        self.assertEqual(
            engine.evaluate("jira_bulk_delete", {}, tainted=False).decision, "ABSENT"
        )


# ---------------------------------------------------------------------------
# Integration: policy wired into MCPPassthrough
# ---------------------------------------------------------------------------


class TestPassthroughPolicyEnforcement(unittest.TestCase):
    def _make(self, source_channel="cli"):
        cfg = AtlassianProxyConfig(
            upstream_url="", mode="proxy", source_channel=source_channel
        )
        policy = ManifestPolicyEngine(_MANIFEST)
        return MCPPassthrough(cfg, policy=policy)

    def test_absent_tool_returns_rpc_error(self):
        pt = self._make()
        resp = pt.forward({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "jira_bulk_delete", "arguments": {}},
        })
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["data"]["decision"], "ABSENT")
        self.assertIn("does not exist", resp["error"]["message"])

    def test_deny_returns_rpc_error_with_rule(self):
        pt = self._make()
        resp = pt.forward({
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": "jira_create_issue", "arguments": {"project_key": "PROD"}},
        })
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["data"]["decision"], "DENY")
        self.assertEqual(resp["error"]["data"]["rule"], "jira_create_restricted_projects")

    def test_tainted_channel_blocks_write(self):
        pt = self._make(source_channel="web")
        resp = pt.forward({
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "jira_create_issue", "arguments": {"project_key": "SAFE"}},
        })
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["data"]["decision"], "DENY")
        self.assertEqual(resp["error"]["data"]["rule"], "tainted_source_blocks_external_write")

    def test_allowed_call_proceeds_to_stub(self):
        pt = self._make()
        resp = pt.forward({
            "jsonrpc": "2.0", "id": 4, "method": "tools/call",
            "params": {"name": "jira_create_issue", "arguments": {"project_key": "SAFE"}},
        })
        # No policy error; stub returns isError=True (no upstream) not a policy block
        self.assertNotIn("error", resp)
        self.assertTrue(resp["result"]["isError"])

    def test_no_policy_always_forwards(self):
        cfg = AtlassianProxyConfig(upstream_url="", mode="proxy")
        pt = MCPPassthrough(cfg)
        resp = pt.forward({
            "jsonrpc": "2.0", "id": 5, "method": "tools/call",
            "params": {"name": "jira_bulk_delete", "arguments": {}},
        })
        # No policy → stub response (not a policy block)
        self.assertNotIn("error", resp)

    def test_policy_decision_logged(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "log.jsonl"
            cfg = AtlassianProxyConfig(upstream_url="", mode="proxy")
            policy = ManifestPolicyEngine(_MANIFEST)
            pt = MCPPassthrough(cfg, log_path=log_path, policy=policy)
            pt.forward({
                "jsonrpc": "2.0", "id": 1, "method": "tools/call",
                "params": {"name": "jira_bulk_delete", "arguments": {}},
            })
            entries = [json.loads(l) for l in log_path.read_text().splitlines()]
            decision_entries = [e for e in entries if e.get("direction") == "decision"]
            self.assertEqual(len(decision_entries), 1)
            self.assertEqual(decision_entries[0]["decision"], "ABSENT")
            self.assertEqual(decision_entries[0]["rule"], "tool_not_allowlisted")

    def test_config_from_env_manifest_path(self):
        manifest_path = str(
            Path(__file__).resolve().parents[1] / "manifests" / "atlassian_mvp.yaml"
        )
        with patch.dict(os.environ, {"ATLASSIAN_MANIFEST_PATH": manifest_path}):
            cfg = AtlassianProxyConfig.from_env()
        self.assertIsNotNone(cfg.manifest_path)
        self.assertEqual(cfg.manifest_path, Path(manifest_path))

    def test_config_from_env_source_channel(self):
        with patch.dict(os.environ, {"ATLASSIAN_SOURCE_CHANNEL": "web"}):
            cfg = AtlassianProxyConfig.from_env()
        self.assertEqual(cfg.source_channel, "web")


if __name__ == "__main__":
    unittest.main()
