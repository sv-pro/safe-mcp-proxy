import unittest
from pathlib import Path

from safe_mcp_proxy.atlassian.adapters import (
    ATLASSIAN_TOOLS,
    COMPOSITE_TOOLS,
    ToolAdapter,
    apply_safe_abstraction,
)
from safe_mcp_proxy.atlassian.passthrough import MCPPassthrough
from safe_mcp_proxy.atlassian.config import AtlassianProxyConfig


# ---------------------------------------------------------------------------
# Registry completeness
# ---------------------------------------------------------------------------


class TestToolRegistry(unittest.TestCase):
    def test_registry_non_empty(self):
        self.assertGreater(len(ATLASSIAN_TOOLS), 0)

    def test_all_entries_are_tool_adapters(self):
        for name, adapter in ATLASSIAN_TOOLS.items():
            self.assertIsInstance(adapter, ToolAdapter)
            self.assertEqual(adapter.name, name)

    def test_service_values_are_valid(self):
        valid = {"jira", "confluence"}
        for adapter in ATLASSIAN_TOOLS.values():
            self.assertIn(adapter.service, valid, adapter.name)

    def test_side_effect_values_are_valid(self):
        for adapter in ATLASSIAN_TOOLS.values():
            self.assertIn(adapter.side_effect, {"read", "write"}, adapter.name)

    def test_jira_read_tools_present(self):
        for name in ("jira_get_issue", "jira_search_issues_using_jql", "jira_get_transitions"):
            self.assertIn(name, ATLASSIAN_TOOLS)

    def test_jira_write_tools_present(self):
        for name in ("jira_create_issue", "jira_update_issue", "jira_transition_issue"):
            self.assertIn(name, ATLASSIAN_TOOLS)

    def test_confluence_read_tools_present(self):
        for name in ("confluence_get_page", "confluence_search_pages"):
            self.assertIn(name, ATLASSIAN_TOOLS)

    def test_composite_tools_list(self):
        self.assertIn("jira_bulk_create_issues", COMPOSITE_TOOLS)
        self.assertIn("jira_delete_issue", COMPOSITE_TOOLS)

    def test_composite_tools_are_not_atomic(self):
        for name in COMPOSITE_TOOLS:
            self.assertFalse(ATLASSIAN_TOOLS[name].atomic, name)

    def test_confluence_get_page_has_safe_alias(self):
        adapter = ATLASSIAN_TOOLS["confluence_get_page"]
        self.assertEqual(adapter.safe_alias, "confluence_get_page_summary")

    def test_read_tools_have_no_safe_alias_by_default(self):
        # Only confluence_get_page currently has one
        without_alias = [
            a for n, a in ATLASSIAN_TOOLS.items()
            if n != "confluence_get_page"
        ]
        for adapter in without_alias:
            self.assertIsNone(adapter.safe_alias, adapter.name)


# ---------------------------------------------------------------------------
# apply_safe_abstraction
# ---------------------------------------------------------------------------


class TestApplySafeAbstraction(unittest.TestCase):
    def _response(self, text: str) -> dict:
        return {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"content": [{"type": "text", "text": text}]},
        }

    def test_no_abstraction_for_unknown_tool(self):
        resp = self._response("hello")
        result = apply_safe_abstraction("unknown_tool", resp)
        self.assertEqual(result, resp)

    def test_no_abstraction_for_tool_without_alias(self):
        resp = self._response("hello")
        result = apply_safe_abstraction("jira_get_issue", resp)
        self.assertEqual(result, resp)

    def test_confluence_get_page_truncates_long_text(self):
        long_text = "x" * 1000
        resp = self._response(long_text)
        result = apply_safe_abstraction("confluence_get_page", resp)
        text = result["result"]["content"][0]["text"]
        self.assertLessEqual(len(text), 510)  # 500 + "…"
        self.assertTrue(text.endswith("…"))
        self.assertTrue(result["result"]["content"][0].get("_truncated"))

    def test_confluence_get_page_short_text_not_truncated(self):
        resp = self._response("short text")
        result = apply_safe_abstraction("confluence_get_page", resp)
        text = result["result"]["content"][0]["text"]
        self.assertEqual(text, "short text")
        self.assertNotIn("_truncated", result["result"]["content"][0])

    def test_abstraction_adds_alias_field(self):
        resp = self._response("content")
        result = apply_safe_abstraction("confluence_get_page", resp)
        self.assertEqual(result["result"]["_abstraction"], "confluence_get_page_summary")

    def test_does_not_mutate_original_response(self):
        long_text = "x" * 1000
        resp = self._response(long_text)
        apply_safe_abstraction("confluence_get_page", resp)
        self.assertEqual(len(resp["result"]["content"][0]["text"]), 1000)

    def test_empty_content_list(self):
        resp = {"jsonrpc": "2.0", "id": 1, "result": {"content": []}}
        result = apply_safe_abstraction("confluence_get_page", resp)
        self.assertEqual(result["result"]["content"], [])

    def test_non_text_blocks_pass_through(self):
        resp = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"content": [{"type": "image", "data": "base64..."}]},
        }
        result = apply_safe_abstraction("confluence_get_page", resp)
        self.assertEqual(result["result"]["content"][0]["type"], "image")


# ---------------------------------------------------------------------------
# Integration: safe abstraction applied in MCPPassthrough
# ---------------------------------------------------------------------------


class TestPassthroughSafeAbstraction(unittest.TestCase):
    def test_confluence_get_page_response_truncated(self):
        cfg = AtlassianProxyConfig(upstream_url="", mode="proxy")
        pt = MCPPassthrough(cfg)

        # Simulate an upstream response by patching _stub_response
        import unittest.mock as mock
        long_text = "z" * 1000
        stub_resp = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"content": [{"type": "text", "text": long_text}]},
        }
        with mock.patch.object(pt, "_stub_response", return_value=stub_resp):
            resp = pt.forward({
                "jsonrpc": "2.0", "id": 1, "method": "tools/call",
                "params": {"name": "confluence_get_page", "arguments": {"page_id": "123"}},
            })
        text = resp["result"]["content"][0]["text"]
        self.assertLessEqual(len(text), 510)
        self.assertEqual(resp["result"]["_abstraction"], "confluence_get_page_summary")

    def test_jira_get_issue_response_not_modified(self):
        cfg = AtlassianProxyConfig(upstream_url="", mode="proxy")
        pt = MCPPassthrough(cfg)
        stub_resp = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"content": [{"type": "text", "text": "PROJ-1: Fix bug"}]},
        }
        import unittest.mock as mock
        with mock.patch.object(pt, "_stub_response", return_value=stub_resp):
            resp = pt.forward({
                "jsonrpc": "2.0", "id": 1, "method": "tools/call",
                "params": {"name": "jira_get_issue", "arguments": {"issue_key": "PROJ-1"}},
            })
        self.assertNotIn("_abstraction", resp.get("result", {}))


# ---------------------------------------------------------------------------
# Manifest consistency check
# ---------------------------------------------------------------------------


class TestManifestConsistency(unittest.TestCase):
    def _load_manifest(self):
        import yaml
        path = Path(__file__).resolve().parents[1] / "manifests" / "atlassian_mvp.yaml"
        with path.open(encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_all_manifest_tools_in_adapter_registry(self):
        manifest = self._load_manifest()
        for tool in manifest.get("allowed_tools", []):
            self.assertIn(tool, ATLASSIAN_TOOLS, f"{tool!r} in manifest but not in adapters")

    def test_no_composite_tools_in_manifest_allowlist(self):
        manifest = self._load_manifest()
        composite = set(COMPOSITE_TOOLS)
        for tool in manifest.get("allowed_tools", []):
            self.assertNotIn(tool, composite, f"Composite tool {tool!r} in allowlist")

    def test_external_write_tools_match_write_adapters(self):
        manifest = self._load_manifest()
        for tool in manifest.get("external_write_tools", []):
            adapter = ATLASSIAN_TOOLS.get(tool)
            self.assertIsNotNone(adapter, tool)
            self.assertEqual(adapter.side_effect, "write", tool)


if __name__ == "__main__":
    unittest.main()
