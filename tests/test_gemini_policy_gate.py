"""Tests for EPIC 8 Issue #91 — Gemini Policy Enforcement Integration."""
import shutil
import tempfile
import textwrap
import unittest
from pathlib import Path

from safe_mcp_proxy.decision import Decision
from safe_mcp_proxy.integrations.gemini.execution_spec import ExecutionSpec
from safe_mcp_proxy.integrations.gemini.adapter import GeminiAdapter
from safe_mcp_proxy.integrations.gemini.policy_gate import GeminiPolicyGate
from safe_mcp_proxy.integrations.gemini.intent_ir import IntentMapper
from safe_mcp_proxy.main import build_executor
from safe_mcp_proxy.provenance import Provenance


_MANIFEST = textwrap.dedent("""\
    world_id: default
    allowed_tools: [read_file, send_email]
    capabilities:
      read_file: {allowed: true}
      send_email: {allowed: true}
    taint_rules:
      - tainted_external: deny
    side_effects: {external: restricted}
""")

_POLICY = "simulation:\n  external_side_effects: true\n"


def _make_executor(manifest: str = _MANIFEST):
    tmp = Path(tempfile.mkdtemp())
    (tmp / "world_manifest.yaml").write_text(manifest, encoding="utf-8")
    cfg = tmp / "safe_mcp_proxy" / "config"
    cfg.mkdir(parents=True)
    (cfg / "policy.yaml").write_text(_POLICY, encoding="utf-8")
    (tmp / "safe_mcp_proxy" / "logs").mkdir(parents=True)
    (tmp / "safe_mcp_proxy" / "logs" / "audit.jsonl").write_text("", encoding="utf-8")
    return build_executor(tmp), tmp


def _tool_call(name: str, args: dict | None = None):
    return GeminiAdapter.parse({"functionCall": {"name": name, "args": args or {}}})


class ExecutionSpecTests(unittest.TestCase):
    def test_is_frozen(self):
        from safe_mcp_proxy.integrations.gemini.intent_ir import IntentIR
        intent = IntentIR(
            action="read_file", parameters={},
            required_capabilities=["read_file"],
            side_effect_type="read", descriptor_hash="abc",
        )
        prov = Provenance.from_source("cli")
        spec = ExecutionSpec(decision=Decision.ALLOW, rule="default_allow",
                             intent=intent, provenance=prov)
        with self.assertRaises((AttributeError, TypeError)):
            spec.decision = Decision.DENY  # type: ignore[misc]

    def test_fields_accessible(self):
        from safe_mcp_proxy.integrations.gemini.intent_ir import IntentIR
        intent = IntentIR(
            action="read_file", parameters={"path": "x"},
            required_capabilities=["read_file"],
            side_effect_type="read", descriptor_hash="abc",
        )
        prov = Provenance.from_source("cli")
        spec = ExecutionSpec(decision=Decision.DENY, rule="descriptor_drift",
                             intent=intent, provenance=prov)
        self.assertIs(spec.decision, Decision.DENY)
        self.assertEqual(spec.rule, "descriptor_drift")
        self.assertIs(spec.intent, intent)
        self.assertIs(spec.provenance, prov)


class GeminiPolicyGateTests(unittest.TestCase):
    def setUp(self):
        self._executor, self._tmp = _make_executor()
        self._gate = GeminiPolicyGate(self._executor)
        self._mapper = IntentMapper(self._executor.registry)

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _evaluate(self, tool_name: str, source: str = "cli",
                  args: dict | None = None) -> ExecutionSpec:
        tool_call = _tool_call(tool_name, args)
        intent = self._mapper.map(tool_call)
        provenance = Provenance.from_source(source)
        return self._gate.evaluate(intent, provenance)

    # ------------------------------------------------------------------
    # ALLOW
    # ------------------------------------------------------------------

    def test_clean_read_file_is_allow(self):
        spec = self._evaluate("read_file", source="cli")
        self.assertIs(spec.decision, Decision.ALLOW)
        self.assertEqual(spec.rule, "default_allow")

    def test_returns_execution_spec_instance(self):
        spec = self._evaluate("read_file")
        self.assertIsInstance(spec, ExecutionSpec)

    def test_spec_carries_intent_and_provenance(self):
        spec = self._evaluate("read_file", source="cli")
        self.assertEqual(spec.intent.action, "read_file")
        self.assertEqual(spec.provenance.source_channel, "cli")

    # ------------------------------------------------------------------
    # DENY
    # ------------------------------------------------------------------

    def test_tainted_send_email_is_deny(self):
        spec = self._evaluate("send_email", source="web")
        self.assertIs(spec.decision, Decision.DENY)
        self.assertEqual(spec.rule, "tainted_external_side_effect")

    def test_tainted_email_from_tool_output_is_deny(self):
        spec = self._evaluate("send_email", source="tool_output")
        self.assertIs(spec.decision, Decision.DENY)

    # ------------------------------------------------------------------
    # ABSENT — allowlist miss
    # ------------------------------------------------------------------

    def test_non_allowlisted_tool_is_absent(self):
        # dangerous_exec is in the catalog but not allowlisted
        spec = self._evaluate("dangerous_exec", source="cli")
        self.assertIs(spec.decision, Decision.ABSENT)
        self.assertEqual(spec.rule, "tool_not_allowlisted")

    # ------------------------------------------------------------------
    # Descriptor drift → DENY
    # ------------------------------------------------------------------

    def test_descriptor_drift_causes_deny(self):
        tool = self._executor.registry.get_tool("read_file")
        original_hash = tool.descriptor_hash
        # Mutate the stored hash to simulate drift
        tool.descriptor_hash = "badhash"
        spec = self._evaluate("read_file", source="cli")
        tool.descriptor_hash = original_hash  # restore
        self.assertIs(spec.decision, Decision.DENY)
        self.assertEqual(spec.rule, "descriptor_drift")

    # ------------------------------------------------------------------
    # ASK — approval_required capability
    # ------------------------------------------------------------------

    def test_approval_required_tool_is_ask(self):
        manifest_with_approval = textwrap.dedent("""\
            world_id: default
            allowed_tools: [read_file, send_email]
            capabilities:
              read_file: {allowed: true}
              send_email: {allowed: true, requires_approval: true}
            taint_rules:
              - tainted_external: deny
            side_effects: {external: restricted}
        """)
        executor, tmp = _make_executor(manifest_with_approval)
        gate = GeminiPolicyGate(executor)
        mapper = IntentMapper(executor.registry)
        tc = _tool_call("send_email")
        intent = mapper.map(tc)
        prov = Provenance.from_source("cli")
        spec = gate.evaluate(intent, prov)
        shutil.rmtree(tmp, ignore_errors=True)
        self.assertIs(spec.decision, Decision.ASK)
        self.assertEqual(spec.rule, "approval_required")


class GeminiPolicyGateIntegrationTests(unittest.TestCase):
    """Verify ExecutionSpec decisions are correctly reflected in the API response."""

    def setUp(self):
        import asyncio
        import httpx
        from api.main import create_app

        executor, self._tmp = _make_executor()
        self._app = create_app(self._tmp, executor=executor)

        async def _post(payload):
            transport = httpx.ASGITransport(app=self._app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
                return await c.post("/integrations/gemini/tools/execute", json=payload)

        self._post = lambda p: asyncio.run(_post(p))

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_deny_from_policy_gate_short_circuits_executor(self):
        # web-tainted send_email → gate says DENY, executor never called
        resp = self._post({
            "functionCall": {"name": "send_email", "args": {}},
            "metadata": {"source_channel": "web"},
        })
        self.assertEqual(resp.status_code, 200)
        body = resp.json()["functionResponse"]["response"]
        self.assertEqual(body["decision"], "DENY")
        self.assertEqual(body["rule"], "tainted_external_side_effect")

    def test_absent_from_policy_gate_short_circuits_executor(self):
        resp = self._post({
            "functionCall": {"name": "dangerous_exec", "args": {}},
            "metadata": {"source_channel": "cli"},
        })
        body = resp.json()["functionResponse"]["response"]
        self.assertEqual(body["decision"], "ABSENT")

    def test_allow_from_policy_gate_reaches_executor(self):
        resp = self._post({
            "functionCall": {"name": "read_file", "args": {"path": "README.md"}},
            "metadata": {"source_channel": "cli"},
        })
        body = resp.json()["functionResponse"]["response"]
        self.assertEqual(body["decision"], "ALLOW")


if __name__ == "__main__":
    unittest.main()
