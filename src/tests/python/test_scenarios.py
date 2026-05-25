import tempfile
import unittest
from pathlib import Path

from safe_mcp_proxy.executor import Executor
from safe_mcp_proxy.main import build_executor
from safe_mcp_proxy.policy_engine import PolicyEngine
from safe_mcp_proxy.registry import ToolRegistry
import safe_mcp_proxy.scenarios as scenarios


def _make_executor(audit_path: str) -> Executor:
    registry = ToolRegistry.with_mock_tools(["read_file", "list_repo", "send_email"])
    policy = PolicyEngine(
        allowlist=["read_file", "list_repo", "send_email"],
        capability_map={"read_file": True, "list_repo": True, "send_email": True},
    )
    return Executor(registry, policy, audit_path, simulate_external=True)


class TestScenarioRegistry(unittest.TestCase):
    def test_all_builtins_registered(self):
        for name in ("benign_flow", "prompt_injection", "poisoned_descriptor", "absent_tool"):
            self.assertIn(name, scenarios.SCENARIOS)

    def test_names_returns_all_builtins(self):
        self.assertTrue({"benign_flow", "prompt_injection", "poisoned_descriptor", "absent_tool"}
                        .issubset(set(scenarios.names())))

    def test_get_known_scenario(self):
        s = scenarios.get("benign_flow")
        self.assertEqual(s.name, "benign_flow")
        self.assertEqual(s.tool, "read_file")
        self.assertEqual(s.source_channel, "cli")
        self.assertEqual(s.expected_decision, "ALLOW")

    def test_get_unknown_raises(self):
        with self.assertRaises(KeyError):
            scenarios.get("nonexistent")

    def test_scenario_has_required_fields(self):
        for name in scenarios.names():
            s = scenarios.get(name)
            self.assertTrue(s.name)
            self.assertTrue(s.description)
            self.assertTrue(s.tool)
            self.assertIn(s.source_channel, ("cli", "email", "web", "tool_output"))
            self.assertIn(s.expected_decision, ("ALLOW", "DENY", "ABSENT", "SIMULATE"))
            self.assertTrue(s.expected_rule)


class TestScenarioRun(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
        self._audit = self._tmp.name
        self._tmp.close()

    def _executor(self):
        return _make_executor(self._audit)

    def test_benign_flow_matches(self):
        out = scenarios.run("benign_flow", executor=self._executor())
        self.assertEqual(out["result"]["decision"], "ALLOW")
        self.assertEqual(out["result"]["rule"], "default_allow")
        self.assertTrue(out["matches"])

    def test_prompt_injection_matches(self):
        out = scenarios.run("prompt_injection", executor=self._executor())
        self.assertEqual(out["result"]["decision"], "DENY")
        self.assertEqual(out["result"]["rule"], "tainted_external_side_effect")
        self.assertTrue(out["matches"])

    def test_poisoned_descriptor_matches(self):
        out = scenarios.run("poisoned_descriptor", executor=self._executor())
        self.assertEqual(out["result"]["decision"], "DENY")
        self.assertEqual(out["result"]["rule"], "descriptor_drift")
        self.assertTrue(out["matches"])

    def test_absent_tool_matches(self):
        out = scenarios.run("absent_tool", executor=self._executor())
        self.assertEqual(out["result"]["decision"], "ABSENT")
        self.assertEqual(out["result"]["rule"], "tool_not_allowlisted")
        self.assertTrue(out["matches"])

    def test_run_result_shape(self):
        out = scenarios.run("benign_flow", executor=self._executor())
        self.assertIn("scenario", out)
        self.assertIn("result", out)
        self.assertIn("expected_decision", out)
        self.assertIn("expected_rule", out)
        self.assertIn("matches", out)

    def test_run_unknown_raises(self):
        with self.assertRaises(KeyError):
            scenarios.run("does_not_exist", executor=self._executor())

    def test_poisoned_descriptor_isolation(self):
        # Each run() with a fresh executor should not affect other executors
        ex1 = self._executor()
        ex2 = self._executor()
        scenarios.run("poisoned_descriptor", executor=ex1)
        # ex2 should still allow read_file normally
        out = scenarios.run("benign_flow", executor=ex2)
        self.assertTrue(out["matches"])
