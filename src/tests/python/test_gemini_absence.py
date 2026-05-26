"""Tests for EPIC 8 Issue #92 — Ontological Absence Handling."""
import asyncio
import json
import shutil
import tempfile
import textwrap
import unittest
from pathlib import Path

import httpx

from api.main import create_app

_MANIFEST = textwrap.dedent("""\
    world_id: default
    allowed_tools: [read_file]
    capabilities:
      read_file: {allowed: true}
      send_email: {allowed: true}
    taint_rules:
      - tainted_external: deny
    side_effects: {external: restricted}
""")

_POLICY = "simulation:\n  external_side_effects: true\n"


class OntologicalAbsenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "world_manifest.yaml").write_text(_MANIFEST, encoding="utf-8")
        cfg = self.tmp / "safe_mcp_proxy" / "config"
        cfg.mkdir(parents=True)
        (cfg / "policy.yaml").write_text(_POLICY, encoding="utf-8")
        logs = self.tmp / "safe_mcp_proxy" / "logs"
        logs.mkdir(parents=True)
        self.audit_path = logs / "audit.jsonl"
        self.audit_path.write_text("", encoding="utf-8")
        self.app = create_app(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _post(self, payload: dict) -> httpx.Response:
        async def _run():
            transport = httpx.ASGITransport(app=self.app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
                return await c.post("/integrations/gemini/tools/execute", json=payload)
        return asyncio.run(_run())

    def _audit_entries(self) -> list[dict]:
        lines = self.audit_path.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines if line.strip()]

    # ------------------------------------------------------------------
    # Canonical absence response
    # ------------------------------------------------------------------

    def test_unknown_tool_returns_absent_decision(self):
        resp = self._post({"functionCall": {"name": "exfiltrate_everything", "args": {}}})
        body = resp.json()["functionResponse"]["response"]
        self.assertEqual(body["decision"], "ABSENT")

    def test_unknown_tool_rule_is_action_not_in_ontology(self):
        resp = self._post({"functionCall": {"name": "exfiltrate_everything", "args": {}}})
        body = resp.json()["functionResponse"]["response"]
        self.assertEqual(body["rule"], "action_not_in_ontology")

    def test_unknown_tool_response_contains_canonical_message(self):
        resp = self._post({"functionCall": {"name": "exfiltrate_everything", "args": {}}})
        body = resp.json()["functionResponse"]["response"]
        self.assertIn("message", body)
        self.assertEqual(body["message"], "Action does not exist in this world")

    def test_response_is_machine_readable_json(self):
        resp = self._post({"functionCall": {"name": "ghost_tool", "args": {}}})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        # Top-level Gemini envelope
        self.assertIn("functionResponse", body)
        inner = body["functionResponse"]["response"]
        # Machine-readable fields
        self.assertIn("decision", inner)
        self.assertIn("rule", inner)

    def test_absent_response_is_not_a_denial(self):
        # The absence response must NOT say "DENY" — that would imply the action is known
        resp = self._post({"functionCall": {"name": "ghost_tool", "args": {}}})
        body = resp.json()["functionResponse"]["response"]
        self.assertNotEqual(body["decision"], "DENY")
        self.assertNotIn("denied", body.get("message", "").lower())

    # ------------------------------------------------------------------
    # Audit trail
    # ------------------------------------------------------------------

    def test_ontological_absence_is_logged_to_audit(self):
        self._post({"functionCall": {"name": "exfiltrate_everything", "args": {}}})
        entries = self._audit_entries()
        self.assertGreater(len(entries), 0)
        absent_entry = next(
            (e for e in entries if e.get("rule") == "action_not_in_ontology"), None
        )
        self.assertIsNotNone(absent_entry, "No audit entry with rule=action_not_in_ontology")

    def test_audit_entry_has_correct_tool_name(self):
        self._post({"functionCall": {"name": "mystery_tool", "args": {}}})
        entries = self._audit_entries()
        entry = next(e for e in entries if e.get("rule") == "action_not_in_ontology")
        self.assertEqual(entry["tool"], "mystery_tool")

    def test_audit_entry_decision_is_absent(self):
        self._post({"functionCall": {"name": "mystery_tool", "args": {}}})
        entries = self._audit_entries()
        entry = next(e for e in entries if e.get("rule") == "action_not_in_ontology")
        self.assertEqual(entry["decision"], "ABSENT")

    def test_tainted_source_reflected_in_audit_entry(self):
        self._post({
            "functionCall": {"name": "mystery_tool", "args": {}},
            "metadata": {"source_channel": "email"},
        })
        entries = self._audit_entries()
        entry = next(e for e in entries if e.get("rule") == "action_not_in_ontology")
        self.assertTrue(entry["taint"])

    # ------------------------------------------------------------------
    # Allowlist ABSENT (known tool, not in this world) still logs via executor
    # ------------------------------------------------------------------

    def test_allowlist_absent_is_also_logged(self):
        # send_email is in the registry but not in the allowed_tools list
        self._post({
            "functionCall": {"name": "send_email", "args": {}},
            "metadata": {"source_channel": "cli"},
        })
        entries = self._audit_entries()
        absent_entries = [e for e in entries if e.get("decision") == "ABSENT"]
        self.assertGreater(len(absent_entries), 0)


if __name__ == "__main__":
    unittest.main()
