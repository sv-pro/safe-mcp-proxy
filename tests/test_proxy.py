import json
import shutil
import tempfile
import textwrap
import unittest
from pathlib import Path

from safe_mcp_proxy.decision import Decision
from safe_mcp_proxy.executor import ABSENT_MESSAGE, Executor
from safe_mcp_proxy.main import build_executor
from safe_mcp_proxy.policy_engine import PolicyEngine
from safe_mcp_proxy.provenance import Provenance
from safe_mcp_proxy.registry import ToolRegistry


class SafeMCPProxyTests(unittest.TestCase):
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


class TestMultipleWorlds(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        worlds_dir = self.tmp / "worlds"
        worlds_dir.mkdir()

        (worlds_dir / "repo_assistant.yaml").write_text(textwrap.dedent("""\
            world_id: repo_assistant
            allowed_tools: [read_file, list_repo, send_email]
            capabilities:
              read_file: {allowed: true}
              list_repo: {allowed: true}
              send_email: {allowed: true}
              dangerous_exec: {allowed: false}
            taint_rules: []
            side_effects: {external: restricted}
        """))

        (worlds_dir / "read_only.yaml").write_text(textwrap.dedent("""\
            world_id: read_only
            allowed_tools: [read_file]
            capabilities:
              read_file: {allowed: true}
              list_repo: {allowed: false}
              send_email: {allowed: false}
              dangerous_exec: {allowed: false}
            taint_rules: []
            side_effects: {external: restricted}
        """))

        # stub policy.yaml so _load_simulation_flag doesn't fail
        config_dir = self.tmp / "safe_mcp_proxy" / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "policy.yaml").write_text("simulation:\n  external_side_effects: true\n")

        # stub logs dir
        logs_dir = self.tmp / "safe_mcp_proxy" / "logs"
        logs_dir.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_send_email_allow_in_full_world_absent_in_read_only(self):
        ex_full = build_executor(self.tmp, world_id="repo_assistant")
        ex_ro = build_executor(self.tmp, world_id="read_only")
        prov = Provenance.from_source("cli")
        result_full = ex_full.execute("send_email", {}, prov)
        result_ro = ex_ro.execute("send_email", {}, prov)
        self.assertEqual(result_full["decision"], "ALLOW")
        self.assertEqual(result_ro["decision"], "ABSENT")

    def test_invalid_world_raises(self):
        with self.assertRaises(FileNotFoundError):
            build_executor(self.tmp, world_id="nonexistent")


if __name__ == "__main__":
    unittest.main()
