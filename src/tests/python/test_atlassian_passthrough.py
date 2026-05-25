import json
import os
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

from safe_mcp_proxy.atlassian.config import AtlassianProxyConfig
from safe_mcp_proxy.atlassian.passthrough import MCPPassthrough


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------


class TestAtlassianProxyConfig(unittest.TestCase):
    def test_defaults(self):
        cfg = AtlassianProxyConfig()
        self.assertEqual(cfg.upstream_url, "")
        self.assertEqual(cfg.mode, "proxy")
        self.assertEqual(cfg.timeout, 30)
        self.assertTrue(cfg.is_proxy_mode)

    def test_from_env(self):
        env = {
            "ATLASSIAN_MCP_URL": "http://localhost:9000",
            "ATLASSIAN_PROXY_MODE": "direct",
            "ATLASSIAN_MCP_TIMEOUT": "15",
        }
        with patch.dict(os.environ, env):
            cfg = AtlassianProxyConfig.from_env()
        self.assertEqual(cfg.upstream_url, "http://localhost:9000")
        self.assertEqual(cfg.mode, "direct")
        self.assertEqual(cfg.timeout, 15)
        self.assertFalse(cfg.is_proxy_mode)

    def test_from_env_defaults_when_vars_absent(self):
        clean = {k: "" for k in ("ATLASSIAN_MCP_URL", "ATLASSIAN_PROXY_MODE", "ATLASSIAN_MCP_TIMEOUT")}
        with patch.dict(os.environ, {}, clear=False):
            for k in ("ATLASSIAN_MCP_URL", "ATLASSIAN_PROXY_MODE", "ATLASSIAN_MCP_TIMEOUT"):
                os.environ.pop(k, None)
            cfg = AtlassianProxyConfig.from_env()
        self.assertEqual(cfg.upstream_url, "")
        self.assertEqual(cfg.mode, "proxy")
        self.assertEqual(cfg.timeout, 30)


# ---------------------------------------------------------------------------
# Passthrough stub responses (no upstream configured)
# ---------------------------------------------------------------------------


class TestMCPPassthroughStub(unittest.TestCase):
    def _make(self, log_path=None):
        cfg = AtlassianProxyConfig(upstream_url="", mode="proxy")
        return MCPPassthrough(cfg, log_path)

    def test_list_tools_returns_empty_tools(self):
        pt = self._make()
        resp = pt.forward({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
        self.assertEqual(resp["jsonrpc"], "2.0")
        self.assertEqual(resp["id"], 1)
        self.assertIn("tools", resp["result"])
        self.assertIsInstance(resp["result"]["tools"], list)

    def test_call_tool_returns_is_error(self):
        pt = self._make()
        resp = pt.forward({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "jira_create_issue", "arguments": {}},
        })
        self.assertEqual(resp["id"], 2)
        self.assertTrue(resp["result"]["isError"])

    def test_initialize_returns_server_info(self):
        pt = self._make()
        resp = pt.forward({"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}})
        self.assertEqual(resp["id"], 0)
        self.assertIn("serverInfo", resp["result"])
        self.assertEqual(resp["result"]["serverInfo"]["name"], "safe-mcp-proxy/atlassian")

    def test_unknown_method_returns_empty_result(self):
        pt = self._make()
        resp = pt.forward({"jsonrpc": "2.0", "id": 99, "method": "notifications/initialized"})
        self.assertEqual(resp["id"], 99)
        self.assertEqual(resp["result"], {})

    def test_direct_mode_also_stubs(self):
        cfg = AtlassianProxyConfig(upstream_url="http://real-upstream", mode="direct")
        pt = MCPPassthrough(cfg)
        resp = pt.forward({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
        self.assertEqual(resp["result"]["tools"], [])


# ---------------------------------------------------------------------------
# Passthrough HTTP forwarding (mocked upstream)
# ---------------------------------------------------------------------------


class TestMCPPassthroughHTTP(unittest.TestCase):
    def _make(self, url="http://upstream:9000"):
        cfg = AtlassianProxyConfig(upstream_url=url, mode="proxy")
        return MCPPassthrough(cfg)

    def _mock_urlopen(self, body: dict):
        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=cm)
        cm.__exit__ = MagicMock(return_value=False)
        cm.read.return_value = json.dumps(body).encode()
        return cm

    def test_forwards_request_and_returns_response(self):
        upstream_resp = {"jsonrpc": "2.0", "id": 1, "result": {"tools": [{"name": "jira_read"}]}}
        pt = self._make()
        with patch("urllib.request.urlopen", return_value=self._mock_urlopen(upstream_resp)):
            resp = pt.forward({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
        self.assertEqual(resp["result"]["tools"][0]["name"], "jira_read")

    def test_url_error_returns_json_rpc_error(self):
        pt = self._make()
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")):
            resp = pt.forward({"jsonrpc": "2.0", "id": 5, "method": "tools/list", "params": {}})
        self.assertIn("error", resp)
        self.assertEqual(resp["id"], 5)
        self.assertEqual(resp["error"]["code"], -32603)

    def test_os_error_returns_json_rpc_error(self):
        pt = self._make()
        with patch("urllib.request.urlopen", side_effect=OSError("connection reset")):
            resp = pt.forward({"jsonrpc": "2.0", "id": 6, "method": "tools/call"})
        self.assertIn("error", resp)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


class TestMCPPassthroughLogging(unittest.TestCase):
    def test_logs_request_and_response(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "logs" / "atlassian_requests.jsonl"
            cfg = AtlassianProxyConfig(upstream_url="", mode="proxy")
            pt = MCPPassthrough(cfg, log_path)
            pt.forward({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})

            lines = log_path.read_text().strip().splitlines()
            self.assertEqual(len(lines), 2)
            req_entry = json.loads(lines[0])
            resp_entry = json.loads(lines[1])
            self.assertEqual(req_entry["direction"], "request")
            self.assertEqual(resp_entry["direction"], "response")
            self.assertIn("timestamp", req_entry)
            self.assertIn("timestamp", resp_entry)

    def test_creates_log_dir_if_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "deep" / "nested" / "log.jsonl"
            cfg = AtlassianProxyConfig()
            MCPPassthrough(cfg, log_path).forward(
                {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
            )
            self.assertTrue(log_path.exists())

    def test_no_log_path_is_silent(self):
        cfg = AtlassianProxyConfig()
        pt = MCPPassthrough(cfg, log_path=None)
        # Must not raise
        pt.forward({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})

    def test_log_appends(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "log.jsonl"
            cfg = AtlassianProxyConfig()
            pt = MCPPassthrough(cfg, log_path)
            pt.forward({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
            pt.forward({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
            lines = log_path.read_text().strip().splitlines()
            self.assertEqual(len(lines), 4)  # 2 pairs of request+response


if __name__ == "__main__":
    unittest.main()
