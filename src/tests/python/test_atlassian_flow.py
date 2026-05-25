import unittest
from pathlib import Path

from safe_mcp_proxy.atlassian.config import AtlassianProxyConfig
from safe_mcp_proxy.atlassian.flow import (
    LABEL_CONFLUENCE_RAW,
    LABEL_CONFLUENCE_SUMMARY,
    FlowContext,
    parse_data_flow_rules,
)
from safe_mcp_proxy.atlassian.passthrough import MCPPassthrough
from safe_mcp_proxy.atlassian.policy import ManifestPolicyEngine

_MANIFEST = {
    "allowed_tools": [
        "jira_get_issue", "jira_create_issue", "jira_add_comment", "confluence_get_page"
    ],
    "external_write_tools": ["jira_create_issue", "jira_add_comment"],
    "arg_rules": {},
    "flow_rules": {"tainted_source_blocks_external_write": True},
    "data_flow_rules": [
        {
            "if_label": LABEL_CONFLUENCE_RAW,
            "deny_for": ["jira_create_issue", "jira_add_comment"],
            "rule": "no_raw_confluence_to_jira",
        }
    ],
}


# ---------------------------------------------------------------------------
# FlowContext unit tests
# ---------------------------------------------------------------------------


class TestFlowContext(unittest.TestCase):
    def test_initially_empty(self):
        fc = FlowContext()
        self.assertEqual(fc.active_labels(), set())

    def test_tag_output_confluence_get_page_raw(self):
        fc = FlowContext()
        fc.tag_output("confluence_get_page", was_abstracted=False)
        self.assertTrue(fc.has_label(LABEL_CONFLUENCE_RAW))
        self.assertFalse(fc.has_label(LABEL_CONFLUENCE_SUMMARY))

    def test_tag_output_confluence_get_page_abstracted(self):
        fc = FlowContext()
        fc.tag_output("confluence_get_page", was_abstracted=True)
        self.assertTrue(fc.has_label(LABEL_CONFLUENCE_SUMMARY))
        self.assertFalse(fc.has_label(LABEL_CONFLUENCE_RAW))

    def test_tag_output_unknown_tool_adds_nothing(self):
        fc = FlowContext()
        fc.tag_output("jira_get_issue", was_abstracted=False)
        self.assertEqual(fc.active_labels(), set())

    def test_clear_removes_all_labels(self):
        fc = FlowContext()
        fc.tag_output("confluence_get_page", was_abstracted=False)
        fc.clear()
        self.assertEqual(fc.active_labels(), set())

    def test_as_dict(self):
        fc = FlowContext()
        fc.tag_output("confluence_get_page", was_abstracted=False)
        d = fc.as_dict()
        self.assertIn("active_labels", d)
        self.assertIn(LABEL_CONFLUENCE_RAW, d["active_labels"])

    def test_labels_accumulate(self):
        fc = FlowContext()
        fc.tag_output("confluence_get_page", was_abstracted=False)
        fc.tag_output("confluence_get_page", was_abstracted=True)
        self.assertIn(LABEL_CONFLUENCE_RAW, fc.active_labels())
        self.assertIn(LABEL_CONFLUENCE_SUMMARY, fc.active_labels())


# ---------------------------------------------------------------------------
# parse_data_flow_rules
# ---------------------------------------------------------------------------


class TestParseDataFlowRules(unittest.TestCase):
    def test_parses_correctly(self):
        raw = [
            {
                "if_label": "confluence_raw",
                "deny_for": ["jira_create_issue"],
                "rule": "no_raw_to_jira",
            }
        ]
        rules = parse_data_flow_rules(raw)
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0].if_label, "confluence_raw")
        self.assertEqual(rules[0].deny_for, ["jira_create_issue"])
        self.assertEqual(rules[0].rule, "no_raw_to_jira")

    def test_default_rule_name(self):
        raw = [{"if_label": "confluence_raw", "deny_for": ["jira_create_issue"]}]
        rules = parse_data_flow_rules(raw)
        self.assertIn("confluence_raw", rules[0].rule)

    def test_empty_list(self):
        self.assertEqual(parse_data_flow_rules([]), [])


# ---------------------------------------------------------------------------
# ManifestPolicyEngine — data_flow_rules
# ---------------------------------------------------------------------------


class TestPolicyEngineDataFlow(unittest.TestCase):
    def _engine(self):
        return ManifestPolicyEngine(_MANIFEST)

    def test_deny_when_confluence_raw_flows_to_jira_write(self):
        fc = FlowContext()
        fc.tag_output("confluence_get_page", was_abstracted=False)
        d = self._engine().evaluate("jira_create_issue", {}, tainted=False, flow_context=fc)
        self.assertEqual(d.decision, "DENY")
        self.assertEqual(d.rule, "no_raw_confluence_to_jira")

    def test_allow_when_confluence_summary_flows_to_jira_write(self):
        # Summary label is not in deny_for → allowed
        fc = FlowContext()
        fc.tag_output("confluence_get_page", was_abstracted=True)
        d = self._engine().evaluate("jira_create_issue", {}, tainted=False, flow_context=fc)
        self.assertEqual(d.decision, "ALLOW")

    def test_allow_jira_read_regardless_of_label(self):
        fc = FlowContext()
        fc.tag_output("confluence_get_page", was_abstracted=False)
        d = self._engine().evaluate("jira_get_issue", {}, tainted=False, flow_context=fc)
        self.assertEqual(d.decision, "ALLOW")

    def test_no_flow_context_skips_data_flow_rules(self):
        d = self._engine().evaluate("jira_create_issue", {}, tainted=False, flow_context=None)
        self.assertEqual(d.decision, "ALLOW")

    def test_empty_flow_context_allows(self):
        fc = FlowContext()  # no labels
        d = self._engine().evaluate("jira_create_issue", {}, tainted=False, flow_context=fc)
        self.assertEqual(d.decision, "ALLOW")

    def test_taint_rule_evaluated_before_data_flow_rule(self):
        # Tainted source → DENY via taint rule (rule 2), not data-flow rule (rule 3)
        fc = FlowContext()
        fc.tag_output("confluence_get_page", was_abstracted=False)
        d = self._engine().evaluate(
            "jira_create_issue", {}, tainted=True, flow_context=fc
        )
        self.assertEqual(d.decision, "DENY")
        self.assertEqual(d.rule, "tainted_source_blocks_external_write")


# ---------------------------------------------------------------------------
# Integration: FlowContext wired into MCPPassthrough
# ---------------------------------------------------------------------------


class TestPassthroughFlowTracking(unittest.TestCase):
    def _make(self, debug=False):
        cfg = AtlassianProxyConfig(upstream_url="", mode="proxy", debug=debug)
        policy = ManifestPolicyEngine(_MANIFEST)
        flow = FlowContext()
        return MCPPassthrough(cfg, policy=policy, flow_context=flow), flow

    def test_confluence_get_page_tags_flow_context(self):
        pt, flow = self._make()
        pt.forward({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "confluence_get_page", "arguments": {"page_id": "123"}},
        })
        self.assertTrue(
            flow.has_label(LABEL_CONFLUENCE_SUMMARY),
            "Expected confluence_summary label (safe abstraction applied)",
        )

    def test_subsequent_jira_create_denied_after_raw_read(self):
        # Manually set raw label (not summary) to simulate no-safe-abstraction scenario
        cfg = AtlassianProxyConfig(upstream_url="", mode="proxy")
        policy = ManifestPolicyEngine(_MANIFEST)
        flow = FlowContext()
        flow.tag_output("confluence_get_page", was_abstracted=False)  # raw label
        pt = MCPPassthrough(cfg, policy=policy, flow_context=flow)

        resp = pt.forward({
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": "jira_create_issue", "arguments": {}},
        })
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["data"]["rule"], "no_raw_confluence_to_jira")

    def test_jira_create_allowed_when_no_flow_context(self):
        cfg = AtlassianProxyConfig(upstream_url="", mode="proxy")
        policy = ManifestPolicyEngine(_MANIFEST)
        pt = MCPPassthrough(cfg, policy=policy, flow_context=None)
        resp = pt.forward({
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "jira_create_issue", "arguments": {}},
        })
        self.assertNotIn("error", resp)

    def test_debug_mode_attaches_flow_context(self):
        pt, flow = self._make(debug=True)
        resp = pt.forward({
            "jsonrpc": "2.0", "id": 4, "method": "tools/call",
            "params": {"name": "confluence_get_page", "arguments": {"page_id": "1"}},
        })
        self.assertIn("_debug", resp.get("result", {}))
        self.assertIn("flow_context", resp["result"]["_debug"])

    def test_debug_mode_false_no_debug_field(self):
        pt, _ = self._make(debug=False)
        resp = pt.forward({
            "jsonrpc": "2.0", "id": 5, "method": "tools/call",
            "params": {"name": "confluence_get_page", "arguments": {"page_id": "1"}},
        })
        self.assertNotIn("_debug", resp.get("result", {}))

    def test_real_manifest_data_flow_rules_loaded(self):
        manifest_path = Path(__file__).resolve().parents[1] / "manifests" / "atlassian_mvp.yaml"
        engine = ManifestPolicyEngine.from_yaml(manifest_path)
        fc = FlowContext()
        fc.tag_output("confluence_get_page", was_abstracted=False)
        d = engine.evaluate("jira_create_issue", {}, tainted=False, flow_context=fc)
        self.assertEqual(d.decision, "DENY")
        self.assertEqual(d.rule, "no_raw_confluence_to_jira")


if __name__ == "__main__":
    unittest.main()
