import json
import os
import unittest
from unittest.mock import MagicMock, patch

from safe_mcp_proxy.atlassian.config import AtlassianProxyConfig
from safe_mcp_proxy.atlassian.filter import CapabilityFilter
from safe_mcp_proxy.atlassian.passthrough import MCPPassthrough

_TOOLS = [
    {"name": "jira_read_issue", "description": "Read a Jira issue"},
    {"name": "jira_create_issue", "description": "Create a Jira issue"},
    {"name": "jira_bulk_create_all_issues", "description": "Bulk-create every issue"},
    {"name": "confluence_read_page", "description": "Read a Confluence page"},
]


# ---------------------------------------------------------------------------
# CapabilityFilter unit tests
# ---------------------------------------------------------------------------


class TestCapabilityFilter(unittest.TestCase):
    def test_passthrough_when_allowlist_empty(self):
        f = CapabilityFilter(allowed_tools=set(), denied_tools=set())
        result = f.filter_tools(_TOOLS)
        self.assertEqual(len(result), len(_TOOLS))

    def test_allowlist_hides_unlisted_tools(self):
        f = CapabilityFilter(allowed_tools={"jira_read_issue"}, denied_tools=set())
        result = f.filter_tools(_TOOLS)
        self.assertEqual([t["name"] for t in result], ["jira_read_issue"])

    def test_denylist_removes_tool_even_if_in_allowlist(self):
        f = CapabilityFilter(
            allowed_tools={"jira_read_issue", "jira_bulk_create_all_issues"},
            denied_tools={"jira_bulk_create_all_issues"},
        )
        result = f.filter_tools(_TOOLS)
        self.assertEqual([t["name"] for t in result], ["jira_read_issue"])

    def test_denylist_without_allowlist(self):
        f = CapabilityFilter(
            allowed_tools=set(),
            denied_tools={"jira_bulk_create_all_issues"},
        )
        result = f.filter_tools(_TOOLS)
        names = [t["name"] for t in result]
        self.assertNotIn("jira_bulk_create_all_issues", names)
        self.assertIn("jira_read_issue", names)
        self.assertEqual(len(result), len(_TOOLS) - 1)

    def test_empty_tools_list(self):
        f = CapabilityFilter(allowed_tools={"jira_read_issue"}, denied_tools=set())
        self.assertEqual(f.filter_tools([]), [])

    def test_tool_without_name_key_is_excluded_by_allowlist(self):
        f = CapabilityFilter(allowed_tools={"jira_read_issue"}, denied_tools=set())
        result = f.filter_tools([{"description": "no name"}])
        self.assertEqual(result, [])

    def test_apply_to_list_response_wraps_result(self):
        f = CapabilityFilter(allowed_tools={"jira_read_issue"}, denied_tools=set())
        response = {"jsonrpc": "2.0", "id": 1, "result": {"tools": _TOOLS}}
        filtered = f.apply_to_list_response(response)
        self.assertEqual(filtered["jsonrpc"], "2.0")
        self.assertEqual(filtered["id"], 1)
        self.assertEqual(len(filtered["result"]["tools"]), 1)
        self.assertEqual(filtered["result"]["tools"][0]["name"], "jira_read_issue")

    def test_apply_to_list_response_does_not_mutate_input(self):
        f = CapabilityFilter(allowed_tools={"jira_read_issue"}, denied_tools=set())
        response = {"jsonrpc": "2.0", "id": 1, "result": {"tools": _TOOLS}}
        f.apply_to_list_response(response)
        self.assertEqual(len(response["result"]["tools"]), len(_TOOLS))


# ---------------------------------------------------------------------------
# Config env-var parsing for allowed/denied tools
# ---------------------------------------------------------------------------


class TestConfigToolsParsing(unittest.TestCase):
    def test_allowed_tools_from_env(self):
        with patch.dict(os.environ, {"ATLASSIAN_ALLOWED_TOOLS": "jira_read_issue, confluence_read_page"}):
            cfg = AtlassianProxyConfig.from_env()
        self.assertEqual(cfg.allowed_tools, {"jira_read_issue", "confluence_read_page"})

    def test_denied_tools_from_env(self):
        with patch.dict(os.environ, {"ATLASSIAN_DENIED_TOOLS": "jira_bulk_create_all_issues"}):
            cfg = AtlassianProxyConfig.from_env()
        self.assertEqual(cfg.denied_tools, {"jira_bulk_create_all_issues"})

    def test_empty_env_gives_empty_sets(self):
        for k in ("ATLASSIAN_ALLOWED_TOOLS", "ATLASSIAN_DENIED_TOOLS"):
            os.environ.pop(k, None)
        cfg = AtlassianProxyConfig.from_env()
        self.assertEqual(cfg.allowed_tools, set())
        self.assertEqual(cfg.denied_tools, set())

    def test_capability_filter_factory(self):
        cfg = AtlassianProxyConfig(
            allowed_tools={"jira_read_issue"},
            denied_tools={"jira_bulk_create_all_issues"},
        )
        f = cfg.capability_filter()
        self.assertIsInstance(f, CapabilityFilter)


# ---------------------------------------------------------------------------
# Integration: filter applied inside MCPPassthrough.forward()
# ---------------------------------------------------------------------------


class TestPassthroughFiltering(unittest.TestCase):
    def _stub_passthrough(self, allowed=None, denied=None):
        cfg = AtlassianProxyConfig(
            upstream_url="",
            mode="proxy",
            allowed_tools=set(allowed or []),
            denied_tools=set(denied or []),
        )
        return MCPPassthrough(cfg)

    def _upstream_passthrough(self, allowed=None, denied=None):
        cfg = AtlassianProxyConfig(
            upstream_url="http://upstream",
            mode="proxy",
            allowed_tools=set(allowed or []),
            denied_tools=set(denied or []),
        )
        return MCPPassthrough(cfg)

    def _mock_upstream(self, tools):
        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=cm)
        cm.__exit__ = MagicMock(return_value=False)
        cm.read.return_value = json.dumps(
            {"jsonrpc": "2.0", "id": 1, "result": {"tools": tools}}
        ).encode()
        return cm

    def test_stub_list_tools_no_filter_returns_empty(self):
        pt = self._stub_passthrough()
        resp = pt.forward({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        self.assertEqual(resp["result"]["tools"], [])

    def test_upstream_list_tools_filtered_by_allowlist(self):
        pt = self._upstream_passthrough(allowed=["jira_read_issue"])
        with patch("urllib.request.urlopen", return_value=self._mock_upstream(_TOOLS)):
            resp = pt.forward({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        self.assertEqual([t["name"] for t in resp["result"]["tools"]], ["jira_read_issue"])

    def test_upstream_list_tools_deny_composite(self):
        pt = self._upstream_passthrough(denied=["jira_bulk_create_all_issues"])
        with patch("urllib.request.urlopen", return_value=self._mock_upstream(_TOOLS)):
            resp = pt.forward({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        names = [t["name"] for t in resp["result"]["tools"]]
        self.assertNotIn("jira_bulk_create_all_issues", names)
        self.assertIn("jira_read_issue", names)

    def test_filter_not_applied_to_other_methods(self):
        pt = self._upstream_passthrough(allowed=["jira_read_issue"])
        upstream_resp = {"jsonrpc": "2.0", "id": 2, "result": {"content": []}}
        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=cm)
        cm.__exit__ = MagicMock(return_value=False)
        cm.read.return_value = json.dumps(upstream_resp).encode()
        with patch("urllib.request.urlopen", return_value=cm):
            resp = pt.forward({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                               "params": {"name": "jira_read_issue", "arguments": {}}})
        self.assertEqual(resp, upstream_resp)


if __name__ == "__main__":
    unittest.main()
