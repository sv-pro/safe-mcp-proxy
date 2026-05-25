import json
import tempfile
import unittest
from pathlib import Path

from safe_mcp_proxy.capability_projection import CapabilityProjectionEngine, ProjectionContext
from safe_mcp_proxy.compiler import SkillCapabilityConfig
from safe_mcp_proxy.executor import Executor, _validate_constraints
from safe_mcp_proxy.execution_mode import ExecutionMode
from safe_mcp_proxy.policy_engine import PolicyEngine
from safe_mcp_proxy.provenance import Provenance
from safe_mcp_proxy.registry import ToolRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cap(
    name: str,
    side_effect: str = "none",
    allowed=True,
    requires_approval: bool = False,
    constraints=None,
    provenance_required=None,
) -> SkillCapabilityConfig:
    return SkillCapabilityConfig(
        name=name,
        source_skill="src:skill",
        exposed_as=name,
        allowed=allowed,
        side_effect=side_effect,
        requires_approval=requires_approval,
        constraints=constraints or {},
        provenance_required=provenance_required,
    )


def _make_executor(caps=None, simulate=True):
    audit = Path(tempfile.gettempdir()) / "guard_test_audit.jsonl"
    return Executor(
        registry=ToolRegistry.with_mock_tools(allowlist=[]),
        policy_engine=PolicyEngine(allowlist=[], capability_map={}),
        audit_log_path=str(audit),
        simulate_external=simulate,
        projection_engine=CapabilityProjectionEngine(),
        skill_capabilities=caps or {},
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


_CLI = Provenance.from_source("cli")
_WEB = Provenance.from_source("web")


# ---------------------------------------------------------------------------
# Constraint validator unit tests
# ---------------------------------------------------------------------------

class TestValidateConstraints(unittest.TestCase):

    def test_no_constraints(self):
        ok, _ = _validate_constraints({}, {"key": "val"})
        self.assertTrue(ok)

    def test_max_bytes_pass(self):
        ok, _ = _validate_constraints({"max_bytes_billed": 1000}, {"bytes_billed": 500})
        self.assertTrue(ok)

    def test_max_bytes_fail(self):
        ok, reason = _validate_constraints({"max_bytes_billed": 1000}, {"bytes_billed": 2000})
        self.assertFalse(ok)
        self.assertEqual(reason, "constraint_violation_bytes_billed")

    def test_deny_pattern_match(self):
        ok, reason = _validate_constraints(
            {"deny_patterns": ["SELECT *"]},
            {"query": "SELECT * FROM users"},
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "constraint_violation_deny_pattern")

    def test_deny_pattern_no_match(self):
        ok, _ = _validate_constraints(
            {"deny_patterns": ["SELECT *"]},
            {"query": "SELECT id FROM users"},
        )
        self.assertTrue(ok)

    def test_allowed_domain_pass(self):
        ok, _ = _validate_constraints(
            {"allowed_domains": ["company.internal"]},
            {"to": "alice@company.internal"},
        )
        self.assertTrue(ok)

    def test_allowed_domain_fail(self):
        ok, reason = _validate_constraints(
            {"allowed_domains": ["company.internal"]},
            {"to": "attacker@example.com"},
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "constraint_violation_domain")

    def test_empty_payload_no_domain_check(self):
        ok, _ = _validate_constraints({"allowed_domains": ["company.internal"]}, {})
        self.assertTrue(ok)


# ---------------------------------------------------------------------------
# Execution guard decision tests
# ---------------------------------------------------------------------------

class TestExecuteSkill(unittest.TestCase):

    # 1. Unknown tool
    def test_unknown_tool_denied(self):
        ex = _make_executor()
        r = ex.execute_skill("nonexistent", {}, _ctx(), _CLI)
        self.assertEqual(r["decision"], "DENY")
        self.assertEqual(r["rule"], "capability_not_defined")

    # 2. allowed == False
    def test_explicitly_disallowed_denied(self):
        ex = _make_executor({"bad": _cap("bad", allowed=False)})
        r = ex.execute_skill("bad", {}, _ctx(), _CLI)
        self.assertEqual(r["decision"], "DENY")
        self.assertEqual(r["rule"], "capability_not_allowed")

    # 3. capability_not_visible (mode/workflow)
    def test_external_communication_denied_in_readonly(self):
        ex = _make_executor({"email": _cap("email", side_effect="external_communication")})
        r = ex.execute_skill("email", {}, _ctx(workflow_id="read_only_research"), _CLI)
        self.assertEqual(r["decision"], "DENY")
        self.assertEqual(r["rule"], "capability_not_visible")

    def test_bounded_compute_denied_in_background(self):
        ex = _make_executor({"bq": _cap("bq", side_effect="bounded_compute")})
        r = ex.execute_skill(
            "bq", {}, _ctx(mode=ExecutionMode.BACKGROUND), _CLI
        )
        self.assertEqual(r["decision"], "DENY")
        self.assertEqual(r["rule"], "capability_not_visible")

    # 4. provenance_violation
    def test_tainted_source_with_provenance_required_denied(self):
        ex = _make_executor({
            "bq": _cap("bq", provenance_required="trusted_or_user_confirmed")
        })
        tainted = Provenance.from_source("web")  # web is tainted
        r = ex.execute_skill("bq", {}, _ctx(), tainted)
        self.assertEqual(r["decision"], "DENY")
        self.assertEqual(r["rule"], "provenance_violation")

    def test_clean_source_with_provenance_required_allowed(self):
        ex = _make_executor({
            "bq": _cap("bq", provenance_required="trusted_or_user_confirmed")
        })
        r = ex.execute_skill("bq", {}, _ctx(), _CLI)
        self.assertEqual(r["decision"], "ALLOW")

    # 5. approval_required
    def test_approval_gated_without_approval_asks(self):
        ex = _make_executor({"gated": _cap("gated", requires_approval=True)})
        r = ex.execute_skill("gated", {}, _ctx(), _CLI)
        self.assertEqual(r["decision"], "ASK")
        self.assertEqual(r["rule"], "approval_required")
        self.assertIsNone(r["result"])

    def test_approval_gated_with_approval_allows(self):
        ex = _make_executor({"gated": _cap("gated", requires_approval=True)})
        ctx = _ctx(approved=frozenset({"gated"}))
        r = ex.execute_skill("gated", {}, ctx, _CLI)
        self.assertEqual(r["decision"], "ALLOW")

    # 6. constraint violations
    def test_constraint_bytes_billed_denied(self):
        ex = _make_executor({
            "bq": _cap("bq", constraints={"max_bytes_billed": 100})
        })
        r = ex.execute_skill("bq", {"bytes_billed": 9999}, _ctx(), _CLI)
        self.assertEqual(r["decision"], "DENY")
        self.assertEqual(r["rule"], "constraint_violation_bytes_billed")

    def test_constraint_deny_pattern_denied(self):
        ex = _make_executor({
            "bq": _cap("bq", constraints={"deny_patterns": ["SELECT *"]})
        })
        r = ex.execute_skill("bq", {"query": "SELECT * FROM t"}, _ctx(), _CLI)
        self.assertEqual(r["decision"], "DENY")
        self.assertEqual(r["rule"], "constraint_violation_deny_pattern")

    def test_constraint_domain_denied(self):
        ex = _make_executor({
            "email": _cap("email", constraints={"allowed_domains": ["company.internal"]},
                          side_effect="external_communication")
        })
        r = ex.execute_skill("email", {"to": "bad@evil.com"}, _ctx(), _CLI)
        self.assertEqual(r["decision"], "DENY")
        self.assertEqual(r["rule"], "constraint_violation_domain")

    def test_constraint_domain_allowed(self):
        ex = _make_executor({
            "email": _cap("email", constraints={"allowed_domains": ["company.internal"]},
                          side_effect="external_communication")
        })
        r = ex.execute_skill("email", {"to": "alice@company.internal"}, _ctx(), _CLI)
        self.assertEqual(r["decision"], "ALLOW")

    # 7. ALLOW
    def test_clean_allow(self):
        ex = _make_executor({"read": _cap("read", side_effect="none")})
        r = ex.execute_skill("read", {}, _ctx(), _CLI)
        self.assertEqual(r["decision"], "ALLOW")
        self.assertEqual(r["rule"], "default_allow")

    # Denied calls never reach adapter
    def test_denied_has_no_side_effect(self):
        """Denied call returns immediately — result contains error, not execution output."""
        ex = _make_executor({"bad": _cap("bad", allowed=False)})
        r = ex.execute_skill("bad", {}, _ctx(), _CLI)
        self.assertIn("error", r["result"])
        self.assertNotIn("ok", r["result"])

    # Audit logging
    def test_deny_is_logged(self):
        audit = Path(tempfile.gettempdir()) / "guard_audit_log_test.jsonl"
        if audit.exists():
            audit.unlink()
        ex = Executor(
            registry=ToolRegistry.with_mock_tools(allowlist=[]),
            policy_engine=PolicyEngine(allowlist=[], capability_map={}),
            audit_log_path=str(audit),
            projection_engine=CapabilityProjectionEngine(),
            skill_capabilities={},
        )
        ex.execute_skill("unknown", {}, _ctx(), _CLI)
        entries = [json.loads(l) for l in audit.read_text().strip().splitlines()]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["decision"], "DENY")
        self.assertEqual(entries[0]["rule"], "capability_not_defined")
        self.assertEqual(entries[0]["workflow_id"], "default_workflow")
        self.assertEqual(entries[0]["identity"], "test-agent")

    def test_allow_is_logged(self):
        audit = Path(tempfile.gettempdir()) / "guard_audit_allow_test.jsonl"
        if audit.exists():
            audit.unlink()
        ex = Executor(
            registry=ToolRegistry.with_mock_tools(allowlist=[]),
            policy_engine=PolicyEngine(allowlist=[], capability_map={}),
            audit_log_path=str(audit),
            projection_engine=CapabilityProjectionEngine(),
            skill_capabilities={"read": _cap("read")},
        )
        ex.execute_skill("read", {}, _ctx(), _CLI)
        entries = [json.loads(l) for l in audit.read_text().strip().splitlines()]
        self.assertEqual(entries[-1]["decision"], "ALLOW")


if __name__ == "__main__":
    unittest.main()
