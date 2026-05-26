import json
import tempfile
import unittest
from pathlib import Path

from safe_mcp_proxy.capability_projection import CapabilityProjectionEngine, ProjectionContext
from safe_mcp_proxy.compiler import SkillCapabilityConfig
from safe_mcp_proxy.executor import Executor
from safe_mcp_proxy.execution_mode import ExecutionMode
from safe_mcp_proxy.policy_engine import PolicyEngine
from safe_mcp_proxy.provenance import Provenance
from safe_mcp_proxy.registry import ToolRegistry


def _cap(name: str, side_effect: str = "none", allowed=True) -> SkillCapabilityConfig:
    return SkillCapabilityConfig(
        name=name, source_skill="src:s", exposed_as=name,
        allowed=allowed, side_effect=side_effect,
    )


def _make_executor(caps=None, world_id="test-world", policy_version="abc12345"):
    audit = Path(tempfile.gettempdir()) / f"trace_test_{world_id}.jsonl"
    if audit.exists():
        audit.unlink()
    return Executor(
        registry=ToolRegistry.with_mock_tools(allowlist=[]),
        policy_engine=PolicyEngine(allowlist=[], capability_map={}),
        audit_log_path=str(audit),
        projection_engine=CapabilityProjectionEngine(),
        skill_capabilities=caps or {},
        world_id=world_id,
        policy_version=policy_version,
    ), audit


def _ctx(workflow_id="default_wf", mode=ExecutionMode.INTERACTIVE):
    return ProjectionContext(identity="test-agent", workflow_id=workflow_id, mode=mode)


def _read_entries(audit: Path):
    return [json.loads(l) for l in audit.read_text().strip().splitlines()]


class TestPolicyTrace(unittest.TestCase):

    # ------------------------------------------------------------------
    # list_tools() audit
    # ------------------------------------------------------------------

    def test_list_tools_logged(self):
        ex, audit = _make_executor({"r": _cap("r")})
        ex.list_tools(_ctx())
        entries = _read_entries(audit)
        self.assertEqual(len(entries), 1)
        e = entries[0]
        self.assertEqual(e["tool"], "list_tools")
        self.assertEqual(e["decision"], "ALLOW")
        self.assertEqual(e["rule"], "projection")

    def test_list_tools_contains_world_id(self):
        ex, audit = _make_executor(world_id="my-world")
        ex.list_tools(_ctx())
        e = _read_entries(audit)[0]
        self.assertEqual(e["world_id"], "my-world")

    def test_list_tools_contains_policy_version(self):
        ex, audit = _make_executor(policy_version="deadbeef")
        ex.list_tools(_ctx())
        e = _read_entries(audit)[0]
        self.assertEqual(e["policy_version"], "deadbeef")

    def test_list_tools_contains_context_fields(self):
        ex, audit = _make_executor()
        ex.list_tools(_ctx(workflow_id="my_workflow", mode=ExecutionMode.BACKGROUND))
        e = _read_entries(audit)[0]
        self.assertEqual(e["identity"], "test-agent")
        self.assertEqual(e["workflow_id"], "my_workflow")
        self.assertEqual(e["mode"], "BACKGROUND")

    def test_list_tools_contains_counts(self):
        caps = {
            "visible": _cap("visible", allowed=True),
            "hidden": _cap("hidden", allowed=False),
        }
        ex, audit = _make_executor(caps)
        ex.list_tools(_ctx())
        e = _read_entries(audit)[0]
        self.assertEqual(e["visible_count"], 1)
        self.assertEqual(e["hidden_count"], 1)

    def test_list_tools_every_call_logged(self):
        ex, audit = _make_executor()
        ex.list_tools(_ctx())
        ex.list_tools(_ctx(workflow_id="wf2"))
        self.assertEqual(len(_read_entries(audit)), 2)

    # ------------------------------------------------------------------
    # execute_skill() audit — trace fields
    # ------------------------------------------------------------------

    def test_execute_skill_deny_contains_world_id_and_version(self):
        ex, audit = _make_executor(world_id="demo", policy_version="cafebabe")
        ex.execute_skill("unknown", {}, _ctx(), Provenance.from_source("cli"))
        e = _read_entries(audit)[0]
        self.assertEqual(e["world_id"], "demo")
        self.assertEqual(e["policy_version"], "cafebabe")

    def test_execute_skill_allow_contains_side_effect(self):
        ex, audit = _make_executor({"bq": _cap("bq", side_effect="none")})
        ex.execute_skill("bq", {}, _ctx(), Provenance.from_source("cli"))
        e = _read_entries(audit)[0]
        self.assertEqual(e["side_effect"], "none")

    def test_execute_skill_deny_contains_side_effect(self):
        ex, audit = _make_executor({"email": _cap("email", side_effect="external_communication", allowed=False)})
        ex.execute_skill("email", {}, _ctx(), Provenance.from_source("cli"))
        e = _read_entries(audit)[0]
        self.assertEqual(e["side_effect"], "external_communication")

    def test_execute_skill_unknown_side_effect_is_empty(self):
        ex, audit = _make_executor()  # no caps
        ex.execute_skill("ghost", {}, _ctx(), Provenance.from_source("cli"))
        e = _read_entries(audit)[0]
        self.assertEqual(e["side_effect"], "")

    def test_execute_skill_contains_source_provenance_list(self):
        ex, audit = _make_executor({"r": _cap("r")})
        ex.execute_skill("r", {}, _ctx(), Provenance.from_source("web"))
        e = _read_entries(audit)[0]
        self.assertIn("source_provenance", e)
        self.assertIsInstance(e["source_provenance"], list)
        self.assertIn("web", e["source_provenance"])

    def test_execute_skill_append_only(self):
        """Each call appends — never overwrites."""
        ex, audit = _make_executor({"r": _cap("r")})
        prov = Provenance.from_source("cli")
        ctx = _ctx()
        ex.execute_skill("r", {}, ctx, prov)
        ex.execute_skill("r", {}, ctx, prov)
        self.assertEqual(len(_read_entries(audit)), 2)

    # ------------------------------------------------------------------
    # Trace schema consistency
    # ------------------------------------------------------------------

    def test_execute_skill_trace_has_required_fields(self):
        required = {"timestamp", "tool", "decision", "rule", "taint", "source_channel",
                    "world_id", "policy_version", "identity", "workflow_id", "mode",
                    "source_provenance", "side_effect"}
        ex, audit = _make_executor({"r": _cap("r")})
        ex.execute_skill("r", {}, _ctx(), Provenance.from_source("cli"))
        e = _read_entries(audit)[0]
        missing = required - set(e.keys())
        self.assertEqual(missing, set(), f"Missing trace fields: {missing}")

    def test_list_tools_trace_has_required_fields(self):
        required = {"timestamp", "tool", "decision", "rule", "world_id", "policy_version",
                    "identity", "workflow_id", "mode", "visible_count", "hidden_count"}
        ex, audit = _make_executor()
        ex.list_tools(_ctx())
        e = _read_entries(audit)[0]
        missing = required - set(e.keys())
        self.assertEqual(missing, set(), f"Missing list_tools trace fields: {missing}")


if __name__ == "__main__":
    unittest.main()
