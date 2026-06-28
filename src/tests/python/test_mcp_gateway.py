"""Tests for safe_mcp_proxy.mcp_gateway — the governed stdio gateway over a real
upstream MCP server.

- TestGatewayUnit drives `handle_request` directly with a fake upstream, so the
  compose logic (allowlist ABSENT filtering + policy routing + forward-on-ALLOW)
  is verified deterministically with no `mcp` SDK and no subprocess.
- TestGatewayIntegration spawns the gateway as a subprocess wired to the bundled
  test upstream via the real UpstreamConnector. Skipped if the `mcp` SDK is absent.
"""
import asyncio
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from safe_mcp_proxy.atlassian.policy import ManifestPolicyEngine
from safe_mcp_proxy.mcp_gateway import handle_request, load_manifest

BASE_DIR = Path(__file__).resolve().parents[3]
SRC_DIR = BASE_DIR / "src" / "main" / "python"
_MCP_AVAILABLE = importlib.util.find_spec("mcp") is not None

# Mirrors the four tools the bundled test upstream exposes.
_UPSTREAM_TOOLS = [
    {"name": "read_file", "description": "Read a file.", "inputSchema": {"type": "object"}},
    {"name": "list_repo", "description": "List repo.", "inputSchema": {"type": "object"}},
    {"name": "send_email", "description": "Send email.", "inputSchema": {"type": "object"}},
    {"name": "dangerous_exec", "description": "Run a command.", "inputSchema": {"type": "object"}},
]

_MANIFEST = {
    "world_id": "test",
    "allowed_tools": ["read_file", "list_repo", "send_email"],  # dangerous_exec ABSENT
    "external_write_tools": ["send_email"],
    "flow_rules": {"tainted_source_blocks_external_write": True},
    "arg_rules": {
        "read_file": [{"arg": "path", "allowed_values": ["README.md"], "rule": "only_readme"}],
    },
}


class FakeUpstream:
    def __init__(self, tools):
        self._tools = tools
        self.calls = []  # records every forwarded call

    async def list_tools(self):
        return self._tools

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        return {"ok": True, "tool": name, "args": arguments}


class TestGatewayUnit(unittest.TestCase):
    def setUp(self):
        self.engine = ManifestPolicyEngine(_MANIFEST)
        self.allowlist = set(_MANIFEST["allowed_tools"])
        self.up = FakeUpstream(_UPSTREAM_TOOLS)

    def _run(self, req, source="cli"):
        return asyncio.run(handle_request(
            req, engine=self.engine, allowlist=self.allowlist,
            upstream=self.up, source_channel=source,
        ))

    def _call(self, name, arguments, source="cli"):
        return self._run(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
             "params": {"name": name, "arguments": arguments}},
            source=source,
        )

    # -- initialize / protocol --------------------------------------------
    def test_initialize_advertises_gateway(self):
        resp = self._run({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        self.assertEqual(resp["result"]["serverInfo"]["name"], "safe-mcp-gateway")
        self.assertIn("tools", resp["result"]["capabilities"])

    def test_notification_returns_none(self):
        resp = self._run({"jsonrpc": "2.0", "method": "notifications/initialized"})
        self.assertIsNone(resp)

    def test_unknown_method_is_error(self):
        resp = self._run({"jsonrpc": "2.0", "id": 7, "method": "nope/foo"})
        self.assertEqual(resp["error"]["code"], -32601)

    # -- tools/list (ABSENT filtering) ------------------------------------
    def test_tools_list_filters_to_allowlist(self):
        resp = self._run({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        names = {t["name"] for t in resp["result"]["tools"]}
        self.assertEqual(names, {"read_file", "list_repo", "send_email"})
        self.assertNotIn("dangerous_exec", names)  # ABSENT — never offered

    # -- tools/call ALLOW forwards ----------------------------------------
    def test_allow_forwards_to_upstream(self):
        resp = self._call("read_file", {"path": "README.md"})
        self.assertFalse(resp["result"].get("isError", False))
        self.assertEqual(self.up.calls, [("read_file", {"path": "README.md"})])
        payload = json.loads(resp["result"]["content"][0]["text"])
        self.assertTrue(payload["ok"])

    # -- tools/call ABSENT not forwarded ----------------------------------
    def test_absent_tool_not_forwarded(self):
        resp = self._call("dangerous_exec", {"command": "rm -rf /"})
        self.assertTrue(resp["result"]["isError"])
        self.assertIn("ABSENT", resp["result"]["content"][0]["text"])
        self.assertEqual(self.up.calls, [])  # upstream never touched

    def test_unknown_tool_not_forwarded(self):
        resp = self._call("no_such_tool", {})
        self.assertTrue(resp["result"]["isError"])
        self.assertEqual(self.up.calls, [])

    # -- tools/call taint floor -------------------------------------------
    def test_tainted_external_write_denied(self):
        resp = self._call("send_email", {"to": "x@y.com", "body": "hi"}, source="web")
        self.assertTrue(resp["result"]["isError"])
        self.assertIn("tainted_source_blocks_external_write", resp["result"]["content"][0]["text"])
        self.assertEqual(self.up.calls, [])

    def test_clean_external_write_allowed(self):
        resp = self._call("send_email", {"to": "x@y.com", "body": "hi"}, source="cli")
        self.assertFalse(resp["result"].get("isError", False))
        self.assertEqual(len(self.up.calls), 1)

    # -- tools/call arg rule ----------------------------------------------
    def test_arg_rule_denies_disallowed_value(self):
        resp = self._call("read_file", {"path": "/etc/passwd"})
        self.assertTrue(resp["result"]["isError"])
        self.assertIn("only_readme", resp["result"]["content"][0]["text"])
        self.assertEqual(self.up.calls, [])

    # -- audit -------------------------------------------------------------
    def test_audit_records_decision(self):
        with tempfile.TemporaryDirectory() as d:
            audit = Path(d) / "audit.jsonl"
            asyncio.run(handle_request(
                {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                 "params": {"name": "dangerous_exec", "arguments": {}}},
                engine=self.engine, allowlist=self.allowlist, upstream=self.up,
                source_channel="cli", audit_path=audit,
            ))
            lines = audit.read_text().strip().splitlines()
            rec = json.loads(lines[-1])
            self.assertEqual(rec["tool"], "dangerous_exec")
            self.assertEqual(rec["decision"], "ABSENT")
            self.assertIn("timestamp", rec)


@unittest.skipUnless(_MCP_AVAILABLE, "mcp SDK not installed")
class TestGatewayIntegration(unittest.TestCase):
    """End-to-end: gateway subprocess ⇄ real UpstreamConnector ⇄ bundled test upstream."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.manifest = Path(self._tmp.name) / "world.yaml"
        # read_file + list_repo allowed; send_email + dangerous_exec ABSENT.
        self.manifest.write_text(
            "world_id: it\nallowed_tools:\n  - read_file\n  - list_repo\n", encoding="utf-8"
        )
        # sanity: the manifest loads
        load_manifest(self.manifest)

    def tearDown(self):
        self._tmp.cleanup()

    def _spawn(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(SRC_DIR)
        args = [
            sys.executable, "-m", "safe_mcp_proxy.mcp_gateway",
            "--manifest", str(self.manifest),
            "--upstream", sys.executable, "-m", "safe_mcp_proxy.mcp_test_server",
        ]
        return subprocess.Popen(
            args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=str(BASE_DIR), env=env,
        )

    @staticmethod
    def _rpc(proc, method, params=None, req_id=1):
        msg = {"jsonrpc": "2.0", "id": req_id, "method": method}
        if params is not None:
            msg["params"] = params
        proc.stdin.write((json.dumps(msg) + "\n").encode())
        proc.stdin.flush()
        return json.loads(proc.stdout.readline())

    @staticmethod
    def _kill(proc):
        for s in (proc.stdin, proc.stdout, proc.stderr):
            try:
                if s:
                    s.close()
            except OSError:
                pass
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

    def test_end_to_end_list_and_call(self):
        proc = self._spawn()
        try:
            init = self._rpc(proc, "initialize", {"protocolVersion": "2024-11-05"})
            self.assertEqual(init["result"]["serverInfo"]["name"], "safe-mcp-gateway")

            listed = self._rpc(proc, "tools/list", req_id=2)
            names = {t["name"] for t in listed["result"]["tools"]}
            self.assertEqual(names, {"read_file", "list_repo"})  # others ABSENT
            self.assertNotIn("dangerous_exec", names)

            allowed = self._rpc(
                proc, "tools/call",
                {"name": "read_file", "arguments": {"path": "README.md"}}, req_id=3,
            )
            self.assertFalse(allowed["result"].get("isError", False))
            self.assertIn("<contents of", allowed["result"]["content"][0]["text"])

            absent = self._rpc(
                proc, "tools/call",
                {"name": "dangerous_exec", "arguments": {"command": "ls"}}, req_id=4,
            )
            self.assertTrue(absent["result"]["isError"])
            self.assertIn("ABSENT", absent["result"]["content"][0]["text"])
        finally:
            self._kill(proc)


if __name__ == "__main__":
    unittest.main()
