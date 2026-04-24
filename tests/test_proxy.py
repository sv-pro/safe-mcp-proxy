import json
import shutil
import tempfile
import textwrap
import unittest
from pathlib import Path

from safe_mcp_proxy.approval_store import ApprovalStore
from safe_mcp_proxy.decision import Decision
from safe_mcp_proxy.execution_mode import ExecutionMode
from safe_mcp_proxy.executor import ABSENT_MESSAGE, Executor
from safe_mcp_proxy.main import build_executor
from safe_mcp_proxy.policy_engine import PolicyEngine
from safe_mcp_proxy.provenance import Provenance
from safe_mcp_proxy.registry import ToolRegistry


class TestProxy(unittest.TestCase):
    def setUp(self):
        self.registry = ToolRegistry.with_mock_tools(["read_file", "list_repo", "send_email"])
        self.policy = PolicyEngine(
            allowlist=["read_file", "list_repo", "send_email"],
            capability_map={"read_file": True, "list_repo": True, "send_email": True},
        )
        self.audit_file = Path(tempfile.gettempdir()) / "safe_mcp_proxy_test_audit.jsonl"
        if self.audit_file.exists():
            self.audit_file.unlink()
        self.executor = Executor(self.registry, self.policy, str(self.audit_file), simulate_external=True)

    def test_benign_cli_read_allows(self):
        result = self.executor.execute("read_file", {"path": "README.md"}, Provenance.from_source("cli"))
        self.assertEqual(result["decision"], "ALLOW")
        self.assertEqual(self.policy.decide("read_file", "read_file", False, "read", True).decision, Decision.ALLOW)

    def test_tainted_external_is_denied(self):
        result = self.executor.execute(
            "send_email",
            {"to": "attacker@example.com", "body": "x"},
            Provenance.from_source("web"),
        )
        self.assertEqual(result["decision"], "DENY")
        self.assertEqual(result["rule"], "tainted_external_side_effect")
        self.assertEqual(
            self.policy.decide("send_email", "send_email", True, "external", True).decision,
            Decision.DENY,
        )

    def test_descriptor_drift_is_denied(self):
        tool = self.registry.get_tool("read_file")
        tool.schema["properties"]["encoding"] = {"type": "string"}
        result = self.executor.execute("read_file", {"path": "README.md"}, Provenance.from_source("cli"))
        self.assertEqual(result["decision"], "DENY")
        self.assertEqual(result["rule"], "descriptor_drift")

    def test_non_allowlisted_tool_is_absent(self):
        result = self.executor.execute("dangerous_exec", {"cmd": "whoami"}, Provenance.from_source("cli"))
        self.assertEqual(result["decision"], "ABSENT")
        self.assertEqual(result["result"]["error"], ABSENT_MESSAGE)
        self.assertEqual(
            self.policy.decide("dangerous_exec", "dangerous_exec", False, "external", True).decision,
            Decision.ABSENT,
        )

    def _last_audit_entry(self):
        with self.audit_file.open() as f:
            return json.loads(f.readlines()[-1])

    def test_replay_allow(self):
        self.executor.execute("read_file", {"path": "README.md"}, Provenance.from_source("cli"))
        result = self.executor.replay(self._last_audit_entry())
        self.assertTrue(result["matches"])
        self.assertEqual(result["replayed_decision"], "ALLOW")

    def test_replay_deny_tainted(self):
        self.executor.execute("send_email", {"to": "x@y.com"}, Provenance.from_source("web"))
        result = self.executor.replay(self._last_audit_entry())
        self.assertTrue(result["matches"])
        self.assertEqual(result["replayed_decision"], "DENY")

    def test_replay_absent(self):
        self.executor.execute("dangerous_exec", {"cmd": "whoami"}, Provenance.from_source("cli"))
        result = self.executor.replay(self._last_audit_entry())
        self.assertTrue(result["matches"])
        self.assertEqual(result["replayed_decision"], "ABSENT")

    def test_replay_100_entries(self):
        scenarios = [
            ("read_file", {"path": "README.md"}, Provenance.from_source("cli")),
            ("send_email", {"to": "x@y.com"}, Provenance.from_source("web")),
            ("dangerous_exec", {"cmd": "whoami"}, Provenance.from_source("cli")),
            ("list_repo", {}, Provenance.from_source("cli")),
        ]
        for i in range(100):
            tool_name, payload, prov = scenarios[i % len(scenarios)]
            self.executor.execute(tool_name, payload, prov)

        entries = [json.loads(line) for line in self.audit_file.read_text().splitlines() if line.strip()]
        self.assertGreaterEqual(len(entries), 100)

        results = [self.executor.replay(e) for e in entries]
        matches = sum(1 for r in results if r["matches"])
        self.assertEqual(matches, len(entries), f"Only {matches}/{len(entries)} entries matched")


class TestASKDecision(unittest.TestCase):
    def setUp(self):
        self.registry = ToolRegistry.with_mock_tools(["read_file", "list_repo", "send_email"])
        self.policy = PolicyEngine(
            allowlist=["read_file", "list_repo", "send_email"],
            capability_map={"read_file": True, "list_repo": True, "send_email": True},
            approval_required={"send_email"},
        )
        self.audit_file = Path(tempfile.gettempdir()) / "safe_mcp_proxy_ask_test_audit.jsonl"
        if self.audit_file.exists():
            self.audit_file.unlink()
        self.store = ApprovalStore()
        self.executor = Executor(
            self.registry, self.policy, str(self.audit_file),
            simulate_external=True, approval_store=self.store,
        )

    def _ask_send_email(self):
        """Helper: trigger ASK for send_email from cli (INTERACTIVE)."""
        prov = Provenance.from_source("cli", execution_mode=ExecutionMode.INTERACTIVE)
        return self.executor.execute("send_email", {"to": "a@b.com"}, prov)

    def test_ask_emitted_for_approval_required_interactive(self):
        result = self._ask_send_email()
        self.assertEqual(result["decision"], "ASK")
        self.assertEqual(result["rule"], "approval_required")
        self.assertIn("approval_token", result)
        self.assertIsNotNone(result["approval_token"])

    def test_ask_falls_back_to_deny_in_background(self):
        prov = Provenance.from_source("cli", execution_mode=ExecutionMode.BACKGROUND)
        result = self.executor.execute("send_email", {"to": "a@b.com"}, prov)
        self.assertEqual(result["decision"], "DENY")
        self.assertEqual(result["rule"], "ask_unavailable_in_background")

    def test_tainted_external_deny_takes_priority_over_ask(self):
        prov = Provenance.from_source("web")
        result = self.executor.execute("send_email", {"to": "a@b.com"}, prov)
        self.assertEqual(result["decision"], "DENY")
        self.assertEqual(result["rule"], "tainted_external_side_effect")

    def test_approve_executes_tool(self):
        ask = self._ask_send_email()
        token = ask["approval_token"]
        self.store.approve(token)
        result = self.executor.execute_approved(token)
        self.assertEqual(result["decision"], "ALLOW")
        self.assertEqual(result["rule"], "approved")
        self.assertIsNotNone(result["result"])

    def test_reject_returns_deny(self):
        ask = self._ask_send_email()
        token = ask["approval_token"]
        result = self.executor.reject_approval(token)
        self.assertEqual(result["decision"], "DENY")
        self.assertEqual(result["rule"], "approval_rejected")

    def test_double_approve_returns_error(self):
        ask = self._ask_send_email()
        token = ask["approval_token"]
        self.store.approve(token)
        self.executor.execute_approved(token)
        # Second approve attempt on already-approved token
        result = self.executor.execute_approved(token)
        self.assertIn("error", result)

    def test_ask_replay_matches_ask(self):
        self._ask_send_email()
        with self.audit_file.open() as f:
            entry = json.loads(f.readlines()[-1])
        self.assertEqual(entry["decision"], "ASK")
        result = self.executor.replay(entry)
        self.assertEqual(result["replayed_decision"], "ASK")
        self.assertTrue(result["matches"])

    def test_execution_mode_propagates_through_derive(self):
        prov = Provenance.from_source("cli", execution_mode=ExecutionMode.BACKGROUND)
        derived = prov.derive("tool_output")
        self.assertEqual(derived.execution_mode, ExecutionMode.BACKGROUND)

    def test_non_approval_required_tool_still_allows(self):
        prov = Provenance.from_source("cli")
        result = self.executor.execute("read_file", {"path": "README.md"}, prov)
        self.assertEqual(result["decision"], "ALLOW")

    def test_policy_engine_ask_decision(self):
        result = self.policy.decide("send_email", "send_email", False, "external", True)
        self.assertEqual(result.decision, Decision.ASK)
        self.assertEqual(result.rule_hit, "approval_required")

    def test_background_audit_logged_as_deny(self):
        prov = Provenance.from_source("cli", execution_mode=ExecutionMode.BACKGROUND)
        self.executor.execute("send_email", {"to": "a@b.com"}, prov)
        with self.audit_file.open() as f:
            entry = json.loads(f.readlines()[-1])
        self.assertEqual(entry["decision"], "DENY")
        self.assertEqual(entry["rule"], "ask_unavailable_in_background")


class TestMultipleWorlds(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        config_dir = self.tmp / "safe_mcp_proxy" / "config"
        worlds_dir = config_dir / "worlds"
        worlds_dir.mkdir(parents=True)

        (worlds_dir / "world_a.yaml").write_text(textwrap.dedent("""\
            world_id: world_a
            allowed_tools: [read_file, list_repo, send_email]
            capabilities:
              read_file: {allowed: true}
              list_repo: {allowed: true}
              send_email: {allowed: true}
              dangerous_exec: {allowed: false}
            taint_rules: []
            side_effects: {external: restricted}
        """))

        (worlds_dir / "world_b.yaml").write_text(textwrap.dedent("""\
            world_id: world_b
            allowed_tools: [read_file]
            capabilities:
              read_file: {allowed: true}
              list_repo: {allowed: false}
              send_email: {allowed: false}
              dangerous_exec: {allowed: false}
            taint_rules: []
            side_effects: {external: restricted}
        """))

        (worlds_dir / "world_c.yaml").write_text(textwrap.dedent("""\
            world_id: world_c
            allowed_tools: [read_file, list_repo, send_email]
            capabilities:
              read_file: {allowed: true}
              list_repo: {allowed: true}
              send_email: {allowed: false}
              dangerous_exec: {allowed: false}
            taint_rules: []
            side_effects: {external: restricted}
        """))

        # stub policy.yaml so _load_simulation_flag doesn't fail
        (config_dir / "policy.yaml").write_text("simulation:\n  external_side_effects: true\n")

        # stub logs dir
        logs_dir = self.tmp / "safe_mcp_proxy" / "logs"
        logs_dir.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_same_input_yields_different_decisions_across_worlds(self):
        ex_world_a = build_executor(self.tmp, world_id="world_a")
        ex_world_b = build_executor(self.tmp, world_id="world_b")
        ex_world_c = build_executor(self.tmp, world_id="world_c")
        prov = Provenance.from_source("cli")

        result_a = ex_world_a.execute("send_email", {}, prov)
        result_b = ex_world_b.execute("send_email", {}, prov)
        result_c = ex_world_c.execute("send_email", {}, prov)

        self.assertEqual(result_a["decision"], "ALLOW")
        self.assertEqual(result_b["decision"], "ABSENT")
        self.assertEqual(result_c["decision"], "ABSENT")
        self.assertEqual(result_c["rule"], "capability_not_allowed")

    def test_invalid_world_raises(self):
        with self.assertRaises(FileNotFoundError):
            build_executor(self.tmp, world_id="nonexistent")


if __name__ == "__main__":
    unittest.main()
