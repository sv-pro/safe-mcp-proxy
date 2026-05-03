"""Tests for EPIC 8 Issue #98 — Gemini Simulate Mode (Safe Replanning Fallback)."""
import asyncio
import json
import shutil
import tempfile
import textwrap
import unittest
from pathlib import Path

import httpx

from api.main import create_app


_MANIFEST_WITH_SIMULATE = textwrap.dedent("""\
    world_id: default
    allowed_tools: [read_file, send_email]
    capabilities:
      read_file: {allowed: true}
      send_email: {allowed: true}
    taint_rules:
      - tainted_external: deny
    side_effects: {external: restricted}
""")

_MANIFEST_NO_SIMULATE = textwrap.dedent("""\
    world_id: default
    allowed_tools: [read_file, send_email]
    capabilities:
      read_file: {allowed: true}
      send_email: {allowed: true}
    taint_rules:
      - tainted_external: deny
    side_effects: {external: restricted}
""")

_POLICY_SIMULATE_ON = "simulation:\n  external_side_effects: true\n"
_POLICY_SIMULATE_OFF = "simulation:\n  external_side_effects: false\n"


def _build_app(tmp: Path, policy_text: str) -> object:
    (tmp / "world_manifest.yaml").write_text(_MANIFEST_WITH_SIMULATE, encoding="utf-8")
    config_dir = tmp / "safe_mcp_proxy" / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "policy.yaml").write_text(policy_text, encoding="utf-8")
    logs_dir = tmp / "safe_mcp_proxy" / "logs"
    logs_dir.mkdir(parents=True)
    (logs_dir / "audit.jsonl").write_text("", encoding="utf-8")
    return create_app(tmp)


def _post(app, payload: dict) -> httpx.Response:
    async def _run():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post("/integrations/gemini/tools/execute", json=payload)
    return asyncio.run(_run())


class TestGeminiSimulateDecision(unittest.TestCase):
    """Simulate path is taken when simulate_external=True + clean source + external tool."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.app = _build_app(self.tmp, _POLICY_SIMULATE_ON)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _send_email_cli(self) -> dict:
        payload = {
            "functionCall": {"name": "send_email", "args": {"to": "a@example.com", "body": "hi"}},
            "metadata": {"source_channel": "cli"},
        }
        return _post(self.app, payload).json()

    def test_clean_external_tool_returns_simulate_decision(self):
        body = self._send_email_cli()
        self.assertEqual(
            body["functionResponse"]["response"]["decision"], "SIMULATE"
        )

    def test_simulate_response_contains_simulated_true(self):
        body = self._send_email_cli()
        self.assertTrue(body["functionResponse"]["response"]["simulated"])

    def test_simulate_result_matches_simulate_external_action_output(self):
        from safe_mcp_proxy.simulate import simulate_external_action
        body = self._send_email_cli()
        self.assertEqual(
            body["functionResponse"]["response"]["result"],
            simulate_external_action(),
        )

    def test_simulate_response_wrapped_in_gemini_envelope(self):
        body = self._send_email_cli()
        self.assertIn("functionResponse", body)
        self.assertEqual(body["functionResponse"]["name"], "send_email")
        self.assertIn("response", body["functionResponse"])

    def test_simulate_rule_is_simulate_external_action(self):
        body = self._send_email_cli()
        self.assertEqual(
            body["functionResponse"]["response"]["rule"], "simulate_external_action"
        )

    def test_simulate_returns_200(self):
        payload = {
            "functionCall": {"name": "send_email", "args": {"to": "a@example.com", "body": "hi"}},
            "metadata": {"source_channel": "cli"},
        }
        resp = _post(self.app, payload)
        self.assertEqual(resp.status_code, 200)


class TestGeminiSimulateAuditLog(unittest.TestCase):
    """SIMULATE decision is recorded in the audit trail with simulated=true."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.app = _build_app(self.tmp, _POLICY_SIMULATE_ON)
        self.audit_path = self.tmp / "safe_mcp_proxy" / "logs" / "audit.jsonl"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_simulate_logged_with_simulate_decision(self):
        payload = {
            "functionCall": {"name": "send_email", "args": {}},
            "metadata": {"source_channel": "cli"},
        }
        _post(self.app, payload)
        entries = [json.loads(l) for l in self.audit_path.read_text().splitlines() if l]
        simulate_entries = [e for e in entries if e.get("decision") == "SIMULATE"]
        self.assertEqual(len(simulate_entries), 1)

    def test_simulate_audit_entry_has_simulated_true(self):
        payload = {
            "functionCall": {"name": "send_email", "args": {}},
            "metadata": {"source_channel": "cli"},
        }
        _post(self.app, payload)
        entries = [json.loads(l) for l in self.audit_path.read_text().splitlines() if l]
        simulate_entry = next(e for e in entries if e.get("decision") == "SIMULATE")
        self.assertTrue(simulate_entry.get("simulated"))

    def test_simulate_audit_entry_has_correct_tool_and_rule(self):
        payload = {
            "functionCall": {"name": "send_email", "args": {}},
            "metadata": {"source_channel": "cli"},
        }
        _post(self.app, payload)
        entries = [json.loads(l) for l in self.audit_path.read_text().splitlines() if l]
        simulate_entry = next(e for e in entries if e.get("decision") == "SIMULATE")
        self.assertEqual(simulate_entry["tool"], "send_email")
        self.assertEqual(simulate_entry["rule"], "simulate_external_action")


class TestGeminiSimulatePrecedence(unittest.TestCase):
    """Other policy rules take precedence over simulate mode."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.app = _build_app(self.tmp, _POLICY_SIMULATE_ON)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_tainted_external_is_still_deny_not_simulate(self):
        payload = {
            "functionCall": {"name": "send_email", "args": {"to": "x@example.com", "body": "hi"}},
            "metadata": {"source_channel": "web"},
        }
        body = _post(self.app, payload).json()
        self.assertEqual(body["functionResponse"]["response"]["decision"], "DENY")
        self.assertEqual(
            body["functionResponse"]["response"]["rule"], "tainted_external_side_effect"
        )

    def test_non_external_tool_with_simulate_mode_is_allow(self):
        payload = {
            "functionCall": {"name": "read_file", "args": {"path": "README.md"}},
            "metadata": {"source_channel": "cli"},
        }
        body = _post(self.app, payload).json()
        self.assertEqual(body["functionResponse"]["response"]["decision"], "ALLOW")

    def test_simulate_mode_off_external_tool_is_allow(self):
        tmp2 = Path(tempfile.mkdtemp())
        try:
            app2 = _build_app(tmp2, _POLICY_SIMULATE_OFF)
            payload = {
                "functionCall": {"name": "send_email", "args": {"to": "x@example.com", "body": "hi"}},
                "metadata": {"source_channel": "cli"},
            }
            body = _post(app2, payload).json()
            self.assertEqual(body["functionResponse"]["response"]["decision"], "ALLOW")
        finally:
            shutil.rmtree(tmp2, ignore_errors=True)

    def test_unknown_tool_is_absent_not_simulate(self):
        payload = {"functionCall": {"name": "exfiltrate_all", "args": {}}}
        body = _post(self.app, payload).json()
        self.assertEqual(body["functionResponse"]["response"]["decision"], "ABSENT")


if __name__ == "__main__":
    unittest.main()
