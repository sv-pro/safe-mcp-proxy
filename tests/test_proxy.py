import tempfile
import unittest
from pathlib import Path

from safe_mcp_proxy.executor import ABSENT_MESSAGE, Executor
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

    def test_tainted_external_is_denied(self):
        result = self.executor.execute(
            "send_email",
            {"to": "attacker@example.com", "body": "x"},
            Provenance.from_source("web"),
        )
        self.assertEqual(result["decision"], "DENY")
        self.assertEqual(result["rule"], "tainted_external_side_effect")

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


if __name__ == "__main__":
    unittest.main()
