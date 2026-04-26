import unittest

from safe_mcp_proxy.capability_projection import (
    CapabilityProjectionEngine,
    ProjectionContext,
    _is_readonly_workflow,
)
from safe_mcp_proxy.compiler import SkillCapabilityConfig
from safe_mcp_proxy.execution_mode import ExecutionMode


def _cap(name: str, side_effect: str = "none", allowed=True, requires_approval: bool = False) -> SkillCapabilityConfig:
    return SkillCapabilityConfig(
        name=name,
        source_skill="src:skill",
        exposed_as=name,
        allowed=allowed,
        side_effect=side_effect,
        requires_approval=requires_approval,
    )


def _ctx(
    workflow_id: str = "default_workflow",
    mode: ExecutionMode = ExecutionMode.INTERACTIVE,
    approved: frozenset = frozenset(),
) -> ProjectionContext:
    return ProjectionContext(
        identity="test-agent",
        workflow_id=workflow_id,
        mode=mode,
        approved_capabilities=approved,
    )


class TestReadonlyWorkflowDetection(unittest.TestCase):

    def test_read_only_prefix(self):
        self.assertTrue(_is_readonly_workflow("read_only_research"))
        self.assertTrue(_is_readonly_workflow("read-only-research"))

    def test_ro_suffix(self):
        self.assertTrue(_is_readonly_workflow("pipeline_ro"))

    def test_not_readonly(self):
        self.assertFalse(_is_readonly_workflow("default_workflow"))
        self.assertFalse(_is_readonly_workflow("interactive_research"))
        self.assertFalse(_is_readonly_workflow("background_job"))


class TestCapabilityProjectionEngine(unittest.TestCase):

    def setUp(self):
        self.engine = CapabilityProjectionEngine()

    def _project(self, caps, ctx):
        return self.engine.project(caps, ctx)

    # ------------------------------------------------------------------
    # allowed == False
    # ------------------------------------------------------------------

    def test_explicitly_disallowed_is_hidden(self):
        caps = {"bad": _cap("bad", allowed=False)}
        result = self._project(caps, _ctx())
        self.assertEqual(result.visible, [])
        self.assertEqual(result.hidden[0], ("bad", "capability_not_allowed"))

    # ------------------------------------------------------------------
    # Background mode
    # ------------------------------------------------------------------

    def test_background_blocks_external_communication(self):
        caps = {"email": _cap("email", side_effect="external_communication")}
        result = self._project(caps, _ctx(mode=ExecutionMode.BACKGROUND))
        self.assertEqual(result.visible, [])
        self.assertEqual(result.hidden[0][1], "side_effect_restricted_in_background")

    def test_background_blocks_deployment(self):
        caps = {"deploy": _cap("deploy", side_effect="deployment")}
        result = self._project(caps, _ctx(mode=ExecutionMode.BACKGROUND))
        self.assertIn(("deploy", "side_effect_restricted_in_background"), result.hidden)

    def test_background_blocks_bounded_compute(self):
        caps = {"bq": _cap("bq", side_effect="bounded_compute")}
        result = self._project(caps, _ctx(mode=ExecutionMode.BACKGROUND))
        self.assertIn(("bq", "side_effect_restricted_in_background"), result.hidden)

    def test_background_allows_none_side_effect(self):
        caps = {"read": _cap("read", side_effect="none")}
        result = self._project(caps, _ctx(mode=ExecutionMode.BACKGROUND))
        self.assertEqual(len(result.visible), 1)
        self.assertEqual(result.visible[0].name, "read")

    def test_background_stricter_than_interactive(self):
        caps = {
            "bq": _cap("bq", side_effect="bounded_compute"),
            "read": _cap("read", side_effect="none"),
        }
        bg = self._project(caps, _ctx(mode=ExecutionMode.BACKGROUND))
        ia = self._project(caps, _ctx(mode=ExecutionMode.INTERACTIVE))
        self.assertLess(len(bg.visible), len(ia.visible))

    # ------------------------------------------------------------------
    # Read-only workflow
    # ------------------------------------------------------------------

    def test_readonly_blocks_external_communication(self):
        caps = {"email": _cap("email", side_effect="external_communication")}
        result = self._project(caps, _ctx(workflow_id="read_only_research"))
        self.assertEqual(result.hidden[0][1], "side_effect_not_allowed_in_workflow")

    def test_readonly_blocks_deployment(self):
        caps = {"deploy": _cap("deploy", side_effect="deployment")}
        result = self._project(caps, _ctx(workflow_id="read_only_research"))
        self.assertIn(("deploy", "side_effect_not_allowed_in_workflow"), result.hidden)

    def test_readonly_blocks_write(self):
        caps = {"write": _cap("write", side_effect="write")}
        result = self._project(caps, _ctx(workflow_id="read_only_research"))
        self.assertIn(("write", "side_effect_not_allowed_in_workflow"), result.hidden)

    def test_readonly_allows_bounded_compute(self):
        caps = {"bq": _cap("bq", side_effect="bounded_compute")}
        result = self._project(caps, _ctx(workflow_id="read_only_research"))
        self.assertEqual(len(result.visible), 1)

    def test_readonly_allows_none(self):
        caps = {"read": _cap("read", side_effect="none")}
        result = self._project(caps, _ctx(workflow_id="read_only_research"))
        self.assertEqual(result.visible[0].name, "read")

    # ------------------------------------------------------------------
    # Approval gating
    # ------------------------------------------------------------------

    def test_approval_required_hidden_without_approval(self):
        caps = {"gated": _cap("gated", requires_approval=True)}
        result = self._project(caps, _ctx())
        self.assertEqual(result.hidden[0], ("gated", "approval_required"))

    def test_approval_required_visible_after_approval(self):
        caps = {"gated": _cap("gated", requires_approval=True)}
        result = self._project(caps, _ctx(approved=frozenset({"gated"})))
        self.assertEqual(result.visible[0].name, "gated")
        self.assertEqual(result.hidden, [])

    # ------------------------------------------------------------------
    # Determinism
    # ------------------------------------------------------------------

    def test_same_inputs_produce_same_result(self):
        caps = {
            "a": _cap("a", side_effect="none"),
            "b": _cap("b", side_effect="external_communication"),
            "c": _cap("c", allowed=False),
        }
        ctx = _ctx(workflow_id="read_only_research", mode=ExecutionMode.INTERACTIVE)
        r1 = self._project(caps, ctx)
        r2 = self._project(caps, ctx)
        self.assertEqual([c.name for c in r1.visible], [c.name for c in r2.visible])
        self.assertEqual(r1.hidden, r2.hidden)

    def test_empty_capabilities(self):
        result = self._project({}, _ctx())
        self.assertEqual(result.visible, [])
        self.assertEqual(result.hidden, [])

    # ------------------------------------------------------------------
    # Executor.list_tools() integration
    # ------------------------------------------------------------------

    def test_executor_list_tools_returns_projected(self):
        import tempfile
        from pathlib import Path
        from safe_mcp_proxy.executor import Executor
        from safe_mcp_proxy.policy_engine import PolicyEngine
        from safe_mcp_proxy.registry import ToolRegistry

        caps = {
            "bq.read": _cap("bq.read", side_effect="none"),
            "email.send": _cap("email.send", side_effect="external_communication"),
        }
        executor = Executor(
            registry=ToolRegistry.with_mock_tools(allowlist=[]),
            policy_engine=PolicyEngine(allowlist=[], capability_map={}),
            audit_log_path=str(Path(tempfile.gettempdir()) / "proj_test_audit.jsonl"),
            projection_engine=CapabilityProjectionEngine(),
            skill_capabilities=caps,
        )
        ctx = _ctx(workflow_id="read_only_research", mode=ExecutionMode.INTERACTIVE)
        result = executor.list_tools(ctx)
        names = [c.name for c in result.visible]
        self.assertIn("bq.read", names)
        self.assertNotIn("email.send", names)

    def test_executor_list_tools_no_engine_returns_empty(self):
        import tempfile
        from pathlib import Path
        from safe_mcp_proxy.executor import Executor
        from safe_mcp_proxy.policy_engine import PolicyEngine
        from safe_mcp_proxy.registry import ToolRegistry

        executor = Executor(
            registry=ToolRegistry.with_mock_tools(allowlist=[]),
            policy_engine=PolicyEngine(allowlist=[], capability_map={}),
            audit_log_path=str(Path(tempfile.gettempdir()) / "proj_test_audit2.jsonl"),
        )
        ctx = _ctx()
        result = executor.list_tools(ctx)
        self.assertEqual(result.visible, [])
        self.assertEqual(result.hidden, [])


if __name__ == "__main__":
    unittest.main()
