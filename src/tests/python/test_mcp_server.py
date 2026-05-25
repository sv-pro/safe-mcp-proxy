"""Tests for the safe_mcp_proxy.mcp_server stdio JSON-RPC transport.

Each test spawns the server as a subprocess with stdin=PIPE / stdout=PIPE,
drives it with JSON-RPC requests, and asserts on the responses.
No external SDK required.
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]


def _spawn(world: str | None = None, mode: str = "interactive") -> subprocess.Popen:
    args = [sys.executable, "-m", "safe_mcp_proxy.mcp_server"]
    if world:
        args += ["--world", world]
    if mode != "interactive":
        args += ["--mode", mode]
    return subprocess.Popen(
        args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(BASE_DIR),
    )


def _call(proc: subprocess.Popen, method: str, params: dict | None = None, req_id: int = 1) -> dict:
    """Send one JSON-RPC request and read one response line."""
    request: dict = {"jsonrpc": "2.0", "id": req_id, "method": method}
    if params is not None:
        request["params"] = params
    proc.stdin.write((json.dumps(request) + "\n").encode())
    proc.stdin.flush()
    line = proc.stdout.readline()
    return json.loads(line)


def _notify(proc: subprocess.Popen, method: str) -> None:
    """Send a notification (no id, no response expected)."""
    msg = {"jsonrpc": "2.0", "method": method}
    proc.stdin.write((json.dumps(msg) + "\n").encode())
    proc.stdin.flush()


def _kill(proc: subprocess.Popen) -> None:
    for stream in (proc.stdin, proc.stdout, proc.stderr):
        try:
            if stream:
                stream.close()
        except OSError:
            pass
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


# ---------------------------------------------------------------------------
# initialize
# ---------------------------------------------------------------------------

class TestInitialize(unittest.TestCase):
    def test_returns_server_name(self):
        proc = _spawn()
        try:
            resp = _call(proc, "initialize", {"protocolVersion": "2024-11-05"})
            self.assertNotIn("error", resp)
            info = resp["result"]["serverInfo"]
            self.assertEqual(info["name"], "safe-mcp-proxy")
        finally:
            _kill(proc)

    def test_returns_version_string(self):
        proc = _spawn()
        try:
            resp = _call(proc, "initialize", {})
            info = resp["result"]["serverInfo"]
            self.assertIn("version", info)
            self.assertIsInstance(info["version"], str)
        finally:
            _kill(proc)

    def test_capabilities_includes_tools(self):
        proc = _spawn()
        try:
            resp = _call(proc, "initialize", {})
            self.assertIn("tools", resp["result"]["capabilities"])
        finally:
            _kill(proc)


# ---------------------------------------------------------------------------
# tools/list
# ---------------------------------------------------------------------------

class TestToolsList(unittest.TestCase):
    def test_returns_only_world_manifest_tools(self):
        """Default world exposes read_file, list_repo, send_email, send_me_email."""
        proc = _spawn()
        try:
            resp = _call(proc, "tools/list")
            names = {t["name"] for t in resp["result"]["tools"]}
            self.assertIn("read_file", names)
            self.assertIn("list_repo", names)
            # dangerous_exec is absent in the default world
            self.assertNotIn("dangerous_exec", names)
        finally:
            _kill(proc)

    def test_read_only_world_has_fewer_tools_than_default(self):
        proc_default = _spawn()
        proc_ro = _spawn(world="read_only")
        try:
            default_tools = _call(proc_default, "tools/list")["result"]["tools"]
            ro_tools = _call(proc_ro, "tools/list")["result"]["tools"]
            self.assertLess(len(ro_tools), len(default_tools))
        finally:
            _kill(proc_default)
            _kill(proc_ro)

    def test_tools_have_required_fields(self):
        proc = _spawn()
        try:
            resp = _call(proc, "tools/list")
            for tool in resp["result"]["tools"]:
                self.assertIn("name", tool)
                self.assertIn("inputSchema", tool)
                self.assertIsInstance(tool["inputSchema"], dict)
        finally:
            _kill(proc)


# ---------------------------------------------------------------------------
# tools/call — ALLOW
# ---------------------------------------------------------------------------

class TestToolsCallAllow(unittest.TestCase):
    def test_allowed_tool_returns_content_block(self):
        proc = _spawn()
        try:
            resp = _call(proc, "tools/call", {"name": "read_file", "arguments": {"path": "README.md"}})
            result = resp["result"]
            self.assertFalse(result.get("isError", False))
            self.assertIsInstance(result["content"], list)
            self.assertEqual(result["content"][0]["type"], "text")
        finally:
            _kill(proc)

    def test_allowed_tool_result_is_valid_json(self):
        proc = _spawn()
        try:
            resp = _call(proc, "tools/call", {"name": "list_repo", "arguments": {}})
            text = resp["result"]["content"][0]["text"]
            data = json.loads(text)
            self.assertIsInstance(data, dict)
        finally:
            _kill(proc)


# ---------------------------------------------------------------------------
# tools/call — ABSENT
# ---------------------------------------------------------------------------

class TestToolsCallAbsent(unittest.TestCase):
    def test_absent_tool_returns_is_error(self):
        """dangerous_exec is not in the default world allowlist → ABSENT."""
        proc = _spawn()
        try:
            resp = _call(proc, "tools/call", {"name": "dangerous_exec", "arguments": {"cmd": "ls"}})
            result = resp["result"]
            self.assertTrue(result.get("isError"))
        finally:
            _kill(proc)

    def test_absent_tool_error_text_contains_absent(self):
        proc = _spawn()
        try:
            resp = _call(proc, "tools/call", {"name": "dangerous_exec", "arguments": {}})
            text = resp["result"]["content"][0]["text"]
            self.assertIn("ABSENT", text)
        finally:
            _kill(proc)

    def test_completely_unknown_tool_returns_is_error(self):
        proc = _spawn()
        try:
            resp = _call(proc, "tools/call", {"name": "no_such_tool_xyz", "arguments": {}})
            self.assertTrue(resp["result"].get("isError"))
        finally:
            _kill(proc)


# ---------------------------------------------------------------------------
# tools/call — DENY / blocked
# ---------------------------------------------------------------------------

class TestToolsCallBlocked(unittest.TestCase):
    def test_ask_tool_in_background_mode_returns_is_error(self):
        """send_email requires_approval → ASK in interactive → DENY in background."""
        proc = _spawn(mode="background")
        try:
            resp = _call(proc, "tools/call", {"name": "send_email", "arguments": {"to": "x@y.com", "body": "hi"}})
            result = resp["result"]
            self.assertTrue(result.get("isError"))
        finally:
            _kill(proc)

    def test_ask_tool_in_interactive_mode_returns_is_error(self):
        """ASK decisions in interactive mode also surface as isError (not ALLOW)."""
        proc = _spawn()
        try:
            resp = _call(proc, "tools/call", {"name": "send_email", "arguments": {"to": "x@y.com", "body": "hi"}})
            result = resp["result"]
            self.assertTrue(result.get("isError"))
        finally:
            _kill(proc)


# ---------------------------------------------------------------------------
# Robustness
# ---------------------------------------------------------------------------

class TestRobustness(unittest.TestCase):
    def test_malformed_json_does_not_crash_server(self):
        """Malformed JSON is logged to stderr; next valid request succeeds."""
        proc = _spawn()
        try:
            proc.stdin.write(b"this is not valid json\n")
            proc.stdin.flush()
            # Server must continue; this valid request should succeed
            resp = _call(proc, "tools/list", req_id=99)
            self.assertIn("tools", resp["result"])
        finally:
            _kill(proc)

    def test_unknown_method_returns_method_not_found(self):
        proc = _spawn()
        try:
            resp = _call(proc, "someUnknownMethod/foo")
            self.assertIn("error", resp)
            self.assertEqual(resp["error"]["code"], -32601)
        finally:
            _kill(proc)

    def test_notifications_initialized_produces_no_response(self):
        """notifications/initialized is a no-op; no stdout line should be emitted for it."""
        proc = _spawn()
        try:
            _notify(proc, "notifications/initialized")
            # Follow with a real request to confirm server is still alive
            resp = _call(proc, "initialize", req_id=2)
            self.assertEqual(resp["result"]["serverInfo"]["name"], "safe-mcp-proxy")
        finally:
            _kill(proc)

    def test_multiple_sequential_requests_all_answered(self):
        proc = _spawn()
        try:
            r1 = _call(proc, "initialize", req_id=1)
            r2 = _call(proc, "tools/list", req_id=2)
            r3 = _call(proc, "tools/call", {"name": "read_file", "arguments": {"path": "x"}}, req_id=3)
            self.assertEqual(r1["id"], 1)
            self.assertEqual(r2["id"], 2)
            self.assertEqual(r3["id"], 3)
        finally:
            _kill(proc)


if __name__ == "__main__":
    unittest.main()
