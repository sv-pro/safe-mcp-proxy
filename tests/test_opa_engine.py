"""Parity and integration tests for OPAPolicyEngine vs PolicyEngine."""

import shutil
import tempfile
import unittest
from pathlib import Path

from safe_mcp_proxy.compiler import build_opa_input
from safe_mcp_proxy.decision import Decision
from safe_mcp_proxy.executor import ABSENT_MESSAGE, Executor
from safe_mcp_proxy.opa_engine import OPAPolicyEngine
from safe_mcp_proxy.policy_engine import PolicyEngine, PolicyResult
from safe_mcp_proxy.provenance import Provenance
from safe_mcp_proxy.registry import ToolRegistry

_OPA_AVAILABLE = shutil.which("opa") is not None

_POLICY_PATH = str(
    Path(__file__).resolve().parents[1]
    / "safe_mcp_proxy"
    / "policies"
    / "proxy.rego"
)

_ALLOWLIST = ["read_file", "list_repo", "send_email"]
_CAPABILITY_MAP = {
    "read_file": True,
    "list_repo": True,
    "send_email": True,
    "dangerous_exec": False,
}


def _make_opa_engine() -> OPAPolicyEngine:
    return OPAPolicyEngine(
        policy_path=_POLICY_PATH,
        allowlist=_ALLOWLIST,
        capability_map=_CAPABILITY_MAP,
    )


def _make_python_engine() -> PolicyEngine:
    return PolicyEngine(allowlist=_ALLOWLIST, capability_map=_CAPABILITY_MAP)


_DECISION_VECTORS = [
    ("read_file", "read_file", False, "read", True, Decision.ALLOW, "default_allow"),
    ("list_repo", "list_repo", False, "internal", True, Decision.ALLOW, "default_allow"),
    ("send_email", "send_email", True, "external", True, Decision.DENY, "tainted_external_side_effect"),
    ("send_email", "send_email", False, "external", False, Decision.DENY, "descriptor_drift"),
    ("dangerous_exec", "dangerous_exec", False, "external", True, Decision.ABSENT, "tool_not_allowlisted"),
]


@unittest.skipUnless(_OPA_AVAILABLE, "opa binary not found — skipping OPA tests")
class TestOPAPolicyEngineDecide(unittest.TestCase):
    """Unit-level parity: OPAPolicyEngine.decide() must agree with all 5 rules."""

    def setUp(self):
        self.opa = _make_opa_engine()
        self.python = _make_python_engine()

    def _check_vector(self, tool, cap, taint, side_effect, hash_valid, exp_decision, exp_rule):
        opa_result = self.opa.decide(tool, cap, taint, side_effect, hash_valid)
        py_result = self.python.decide(tool, cap, taint, side_effect, hash_valid)
        self.assertEqual(opa_result.decision, exp_decision, f"OPA decision mismatch for tool={tool!r}")
        self.assertEqual(opa_result.rule_hit, exp_rule, f"OPA rule_hit mismatch for tool={tool!r}")
        self.assertEqual(
            opa_result.decision, py_result.decision,
            f"OPA/Python parity mismatch (decision) for tool={tool!r}",
        )
        self.assertEqual(
            opa_result.rule_hit, py_result.rule_hit,
            f"OPA/Python parity mismatch (rule_hit) for tool={tool!r}",
        )

    def test_benign_cli_read_allows(self):
        self._check_vector("read_file", "read_file", False, "read", True, Decision.ALLOW, "default_allow")

    def test_benign_list_repo_allows(self):
        self._check_vector("list_repo", "list_repo", False, "internal", True, Decision.ALLOW, "default_allow")

    def test_tainted_external_is_denied(self):
        self._check_vector("send_email", "send_email", True, "external", True, Decision.DENY, "tainted_external_side_effect")

    def test_descriptor_drift_is_denied(self):
        self._check_vector("send_email", "send_email", False, "external", False, Decision.DENY, "descriptor_drift")

    def test_non_allowlisted_tool_is_absent(self):
        self._check_vector("dangerous_exec", "dangerous_exec", False, "external", True, Decision.ABSENT, "tool_not_allowlisted")

    def test_capability_not_allowed_is_absent(self):
        opa = OPAPolicyEngine(
            policy_path=_POLICY_PATH,
            allowlist=["read_file", "list_repo", "send_email"],
            capability_map={"read_file": True, "list_repo": True, "send_email": False},
        )
        py = PolicyEngine(
            allowlist=["read_file", "list_repo", "send_email"],
            capability_map={"read_file": True, "list_repo": True, "send_email": False},
        )
        opa_result = opa.decide("send_email", "send_email", False, "external", True)
        py_result = py.decide("send_email", "send_email", False, "external", True)
        self.assertEqual(opa_result.decision, Decision.ABSENT)
        self.assertEqual(opa_result.rule_hit, "capability_not_allowed")
        self.assertEqual(opa_result.decision, py_result.decision)
        self.assertEqual(opa_result.rule_hit, py_result.rule_hit)

    def test_full_parity_across_all_vectors(self):
        """All five decision paths: OPA and Python must agree on every vector."""
        for vector in _DECISION_VECTORS:
            with self.subTest(tool=vector[0], expected=vector[5].value):
                self._check_vector(*vector)


@unittest.skipUnless(_OPA_AVAILABLE, "opa binary not found — skipping OPA tests")
class TestOPAExecutorIntegration(unittest.TestCase):
    """End-to-end: Executor wired with OPAPolicyEngine produces same results as with PolicyEngine."""

    def setUp(self):
        self.registry = ToolRegistry.with_mock_tools(_ALLOWLIST)
        self.audit_file = Path(tempfile.gettempdir()) / "safe_mcp_proxy_opa_test_audit.jsonl"
        if self.audit_file.exists():
            self.audit_file.unlink()
        self.opa_executor = Executor(
            self.registry,
            _make_opa_engine(),
            str(self.audit_file),
            simulate_external=True,
        )
        self.py_executor = Executor(
            self.registry,
            _make_python_engine(),
            str(self.audit_file),
            simulate_external=True,
        )

    def _compare(self, tool, payload, source):
        prov = Provenance.from_source(source)
        opa_res = self.opa_executor.execute(tool, payload, prov)
        py_res = self.py_executor.execute(tool, payload, prov)
        self.assertEqual(opa_res["decision"], py_res["decision"], f"decision mismatch for {tool!r}")
        self.assertEqual(opa_res["rule"], py_res["rule"], f"rule mismatch for {tool!r}")

    def test_benign_cli_read(self):
        self._compare("read_file", {"path": "README.md"}, "cli")

    def test_tainted_external_send_email(self):
        self._compare("send_email", {"to": "attacker@example.com"}, "web")

    def test_absent_dangerous_exec(self):
        self._compare("dangerous_exec", {"cmd": "whoami"}, "cli")

    def test_clean_send_email_allowed(self):
        self._compare("send_email", {"to": "user@example.com"}, "cli")

    def test_all_vectors_parity(self):
        scenarios = [
            ("read_file", {"path": "README.md"}, "cli"),
            ("send_email", {"to": "x@y.com"}, "web"),
            ("dangerous_exec", {"cmd": "whoami"}, "cli"),
            ("list_repo", {}, "cli"),
            ("send_email", {"to": "clean@example.com"}, "cli"),
        ]
        for tool, payload, source in scenarios:
            with self.subTest(tool=tool, source=source):
                self._compare(tool, payload, source)


class TestBuildOpaInput(unittest.TestCase):
    """Unit tests for the build_opa_input() helper (no OPA binary required)."""

    def test_output_structure(self):
        result = build_opa_input(
            tool_name="read_file",
            capability="read_file",
            taint=False,
            side_effect_type="read",
            descriptor_hash_valid=True,
            allowlist=["read_file"],
            capability_map={"read_file": True},
        )
        self.assertEqual(result["tool_name"], "read_file")
        self.assertEqual(result["capability"], "read_file")
        self.assertFalse(result["taint"])
        self.assertEqual(result["side_effect_type"], "read")
        self.assertTrue(result["descriptor_hash_valid"])
        self.assertEqual(result["allowlist"], ["read_file"])
        self.assertEqual(result["capability_map"], {"read_file": True})

    def test_allowlist_is_list(self):
        result = build_opa_input("x", "x", False, "read", True, ("a", "b"), {})
        self.assertIsInstance(result["allowlist"], list)

    def test_capability_map_is_dict(self):
        result = build_opa_input("x", "x", False, "read", True, [], {"a": True})
        self.assertIsInstance(result["capability_map"], dict)


class TestOPAEngineNoOPA(unittest.TestCase):
    """Verify that OPAPolicyEngine raises a helpful error when OPA is absent."""

    @unittest.skipIf(_OPA_AVAILABLE, "opa binary present — skipping no-opa guard test")
    def test_raises_when_opa_missing(self):
        with self.assertRaises(RuntimeError) as ctx:
            OPAPolicyEngine(policy_path="proxy.rego", allowlist=[], capability_map={})
        self.assertIn("OPA binary not found", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
