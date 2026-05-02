"""Tests for EPIC 8 Issue #90 — Intent IR Mapping (ToolCall → IntentIR)."""
import unittest

from safe_mcp_proxy.integrations.gemini_adapter import GeminiAdapter
from safe_mcp_proxy.integrations.intent_ir import IntentIR, IntentIRError, IntentMapper
from safe_mcp_proxy.registry import ToolRegistry


def _make_registry(allowlist=("read_file",)) -> ToolRegistry:
    return ToolRegistry.with_mock_tools(allowlist=allowlist)


class IntentIRDataclassTests(unittest.TestCase):
    def test_is_frozen(self):
        ir = IntentIR(
            action="read_file",
            parameters={"path": "README.md"},
            required_capabilities=["read_file"],
            side_effect_type="read",
            descriptor_hash="abc123",
        )
        with self.assertRaises((AttributeError, TypeError)):
            ir.action = "other"  # type: ignore[misc]

    def test_fields_are_accessible(self):
        ir = IntentIR(
            action="send_email",
            parameters={"to": "a@b.com"},
            required_capabilities=["send_email"],
            side_effect_type="external",
            descriptor_hash="deadbeef",
        )
        self.assertEqual(ir.action, "send_email")
        self.assertEqual(ir.parameters, {"to": "a@b.com"})
        self.assertEqual(ir.required_capabilities, ["send_email"])
        self.assertEqual(ir.side_effect_type, "external")
        self.assertEqual(ir.descriptor_hash, "deadbeef")


class IntentIRErrorTests(unittest.TestCase):
    def test_carries_action_name(self):
        err = IntentIRError("exfiltrate_everything")
        self.assertEqual(err.action, "exfiltrate_everything")

    def test_is_key_error_subclass(self):
        self.assertIsInstance(IntentIRError("x"), KeyError)

    def test_message_contains_action(self):
        err = IntentIRError("bad_tool")
        self.assertIn("bad_tool", str(err))


class IntentMapperTests(unittest.TestCase):
    def setUp(self):
        # allowlist only read_file; send_email is registered but not exposed
        self._registry = _make_registry(allowlist=("read_file",))
        self._mapper = IntentMapper(self._registry)

    def _make_tool_call(self, name: str, args: dict | None = None):
        return GeminiAdapter.parse({
            "functionCall": {"name": name, "args": args or {}},
        })

    # ------------------------------------------------------------------
    # Happy-path mapping
    # ------------------------------------------------------------------

    def test_maps_allowlisted_tool(self):
        tool_call = self._make_tool_call("read_file", {"path": "README.md"})
        ir = self._mapper.map(tool_call)
        self.assertIsInstance(ir, IntentIR)
        self.assertEqual(ir.action, "read_file")
        self.assertEqual(ir.parameters, {"path": "README.md"})

    def test_required_capabilities_contains_tool_capability(self):
        tool_call = self._make_tool_call("read_file")
        ir = self._mapper.map(tool_call)
        self.assertIn("read_file", ir.required_capabilities)

    def test_side_effect_type_is_populated(self):
        tool_call = self._make_tool_call("read_file")
        ir = self._mapper.map(tool_call)
        self.assertIsNotNone(ir.side_effect_type)
        self.assertIsInstance(ir.side_effect_type, str)

    def test_descriptor_hash_is_populated(self):
        tool_call = self._make_tool_call("read_file")
        ir = self._mapper.map(tool_call)
        self.assertIsNotNone(ir.descriptor_hash)
        self.assertGreater(len(ir.descriptor_hash), 0)

    def test_empty_args_become_empty_parameters(self):
        tool_call = self._make_tool_call("read_file")
        ir = self._mapper.map(tool_call)
        self.assertEqual(ir.parameters, {})

    # ------------------------------------------------------------------
    # Ontology membership: known but not allowlisted still maps
    # ------------------------------------------------------------------

    def test_maps_known_but_non_allowlisted_tool(self):
        # send_email is in the registry's full catalog even though not allowlisted
        tool_call = self._make_tool_call("send_email", {"to": "x@example.com"})
        ir = self._mapper.map(tool_call)
        self.assertEqual(ir.action, "send_email")
        self.assertEqual(ir.side_effect_type, "external")

    # ------------------------------------------------------------------
    # Unknown tool → IntentIRError
    # ------------------------------------------------------------------

    def test_completely_unknown_tool_raises_intent_ir_error(self):
        tool_call = self._make_tool_call("exfiltrate_everything")
        with self.assertRaises(IntentIRError) as ctx:
            self._mapper.map(tool_call)
        self.assertEqual(ctx.exception.action, "exfiltrate_everything")

    def test_empty_name_raises_intent_ir_error(self):
        # GeminiAdapter rejects empty name, but we test mapper directly
        from safe_mcp_proxy.integrations.gemini_adapter import ToolCall
        tool_call = ToolCall(
            tool_name="ghost_tool",
            arguments={},
            session_id=None,
            agent_id=None,
            metadata={},
            raw_request={},
        )
        with self.assertRaises(IntentIRError):
            self._mapper.map(tool_call)


class IntentMapperIntegrationTests(unittest.TestCase):
    """Verify IntentMapper is correctly wired into GeminiProxy.execute()."""

    def setUp(self):
        import shutil
        import tempfile
        import textwrap
        from pathlib import Path
        from api.main import create_app

        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "world_manifest.yaml").write_text(textwrap.dedent("""\
            world_id: default
            allowed_tools: [read_file]
            capabilities:
              read_file: {allowed: true}
            taint_rules:
              - tainted_external: deny
            side_effects: {external: restricted}
        """), encoding="utf-8")
        config_dir = self.tmp / "safe_mcp_proxy" / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "policy.yaml").write_text(
            "simulation:\n  external_side_effects: true\n", encoding="utf-8"
        )
        (self.tmp / "safe_mcp_proxy" / "logs").mkdir(parents=True)
        (self.tmp / "safe_mcp_proxy" / "logs" / "audit.jsonl").write_text("", encoding="utf-8")
        self.app = create_app(self.tmp)
        self._shutil = shutil

    def tearDown(self):
        self._shutil.rmtree(self.tmp, ignore_errors=True)

    def _post(self, payload: dict):
        import asyncio
        import httpx

        async def _run():
            transport = httpx.ASGITransport(app=self.app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                return await client.post("/integrations/gemini/tools/execute", json=payload)
        return asyncio.run(_run())

    def test_ontologically_absent_tool_returns_action_not_in_ontology(self):
        payload = {"functionCall": {"name": "exfiltrate_everything", "args": {}}}
        resp = self._post(payload)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["functionResponse"]["response"]["decision"], "ABSENT")
        self.assertEqual(body["functionResponse"]["response"]["rule"], "action_not_in_ontology")

    def test_allowlist_absent_tool_returns_executor_absent(self):
        # send_email is in the catalog but not in the allowlist → executor ABSENT
        payload = {"functionCall": {"name": "send_email", "args": {}}}
        resp = self._post(payload)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["functionResponse"]["response"]["decision"], "ABSENT")


if __name__ == "__main__":
    unittest.main()
