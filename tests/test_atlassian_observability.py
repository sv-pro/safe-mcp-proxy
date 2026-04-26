"""Tests for Atlassian MCP observability: trace_id, TraceReader, CLI."""
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from safe_mcp_proxy.atlassian.cli import main as cli_main
from safe_mcp_proxy.atlassian.config import AtlassianProxyConfig
from safe_mcp_proxy.atlassian.flow import FlowContext
from safe_mcp_proxy.atlassian.passthrough import MCPPassthrough
from safe_mcp_proxy.atlassian.policy import ManifestPolicyEngine
from safe_mcp_proxy.atlassian.trace_reader import AtlassianTraceReader, TraceEntry

_MANIFEST = {
    "allowed_tools": ["jira_get_issue", "jira_create_issue", "confluence_get_page"],
    "external_write_tools": ["jira_create_issue"],
    "arg_rules": {},
    "flow_rules": {"tainted_source_blocks_external_write": True},
    "data_flow_rules": [],
}


def _make_proxy(log_path=None):
    cfg = AtlassianProxyConfig(upstream_url="", mode="proxy")
    policy = ManifestPolicyEngine(_MANIFEST)
    return MCPPassthrough(cfg, log_path=log_path, policy=policy)


# ---------------------------------------------------------------------------
# trace_id in log entries
# ---------------------------------------------------------------------------


class TestTraceId(unittest.TestCase):
    def test_all_entries_for_one_call_share_trace_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "log.jsonl"
            pt = _make_proxy(log_path)
            pt.forward({
                "jsonrpc": "2.0", "id": 1, "method": "tools/call",
                "params": {"name": "jira_get_issue", "arguments": {"issue_key": "PROJ-1"}},
            })
            lines = [json.loads(l) for l in log_path.read_text().splitlines()]

        trace_ids = {l["trace_id"] for l in lines}
        self.assertEqual(len(trace_ids), 1, "All entries in one forward() must share trace_id")

    def test_different_calls_have_different_trace_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "log.jsonl"
            pt = _make_proxy(log_path)
            pt.forward({
                "jsonrpc": "2.0", "id": 1, "method": "tools/call",
                "params": {"name": "jira_get_issue", "arguments": {}},
            })
            pt.forward({
                "jsonrpc": "2.0", "id": 2, "method": "tools/call",
                "params": {"name": "jira_get_issue", "arguments": {}},
            })
            lines = [json.loads(l) for l in log_path.read_text().splitlines()]

        # Each call produces request + decision + response = 3 entries
        trace_ids = {l["trace_id"] for l in lines}
        self.assertEqual(len(trace_ids), 2)

    def test_blocked_call_has_trace_id_in_all_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "log.jsonl"
            pt = _make_proxy(log_path)
            pt.forward({
                "jsonrpc": "2.0", "id": 1, "method": "tools/call",
                "params": {"name": "jira_bulk_delete", "arguments": {}},
            })
            lines = [json.loads(l) for l in log_path.read_text().splitlines()]

        self.assertTrue(all("trace_id" in l for l in lines))
        trace_ids = {l["trace_id"] for l in lines}
        self.assertEqual(len(trace_ids), 1)

    def test_trace_id_is_uuid_format(self):
        import re
        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        )
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "log.jsonl"
            _make_proxy(log_path).forward({
                "jsonrpc": "2.0", "id": 1, "method": "tools/call",
                "params": {"name": "jira_get_issue", "arguments": {}},
            })
            line = json.loads(log_path.read_text().splitlines()[0])
        self.assertRegex(line["trace_id"], uuid_pattern)


# ---------------------------------------------------------------------------
# AtlassianTraceReader
# ---------------------------------------------------------------------------


class TestAtlassianTraceReader(unittest.TestCase):
    def _write_log(self, tmp, entries):
        log_path = Path(tmp) / "log.jsonl"
        with log_path.open("w") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")
        return log_path

    def _sample_entries(self):
        return [
            {"direction": "request", "timestamp": "2026-01-01T00:00:00Z",
             "trace_id": "aaa", "payload": {}},
            {"direction": "decision", "timestamp": "2026-01-01T00:00:01Z",
             "trace_id": "aaa", "tool": "jira_get_issue", "decision": "ALLOW",
             "rule": "default_allow", "tainted": False, "flow_labels": []},
            {"direction": "response", "timestamp": "2026-01-01T00:00:02Z",
             "trace_id": "aaa", "payload": {}},
            {"direction": "request", "timestamp": "2026-01-01T00:01:00Z",
             "trace_id": "bbb", "payload": {}},
            {"direction": "decision", "timestamp": "2026-01-01T00:01:01Z",
             "trace_id": "bbb", "tool": "jira_create_issue", "decision": "DENY",
             "rule": "tainted_source_blocks_external_write", "tainted": True,
             "flow_labels": []},
            {"direction": "response", "timestamp": "2026-01-01T00:01:02Z",
             "trace_id": "bbb", "payload": {}},
        ]

    def test_all_returns_all_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = self._write_log(tmp, self._sample_entries())
            entries = AtlassianTraceReader(log_path).all()
        self.assertEqual(len(entries), 6)

    def test_decisions_returns_only_decisions(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = self._write_log(tmp, self._sample_entries())
            decisions = AtlassianTraceReader(log_path).decisions()
        self.assertEqual(len(decisions), 2)
        self.assertTrue(all(e.direction == "decision" for e in decisions))

    def test_filter_by_decision(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = self._write_log(tmp, self._sample_entries())
            denied = AtlassianTraceReader(log_path).filter(decision="DENY")
        self.assertEqual(len(denied), 1)
        self.assertEqual(denied[0].tool, "jira_create_issue")

    def test_filter_by_tool(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = self._write_log(tmp, self._sample_entries())
            result = AtlassianTraceReader(log_path).filter(tool="jira_get_issue")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].decision, "ALLOW")

    def test_filter_last(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = self._write_log(tmp, self._sample_entries())
            result = AtlassianTraceReader(log_path).filter(last=1)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].trace_id, "bbb")

    def test_by_trace_returns_all_entries_for_trace(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = self._write_log(tmp, self._sample_entries())
            result = AtlassianTraceReader(log_path).by_trace("aaa")
        self.assertEqual(len(result), 3)
        self.assertTrue(all(e.trace_id == "aaa" for e in result))

    def test_stats(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = self._write_log(tmp, self._sample_entries())
            stats = AtlassianTraceReader(log_path).stats()
        self.assertEqual(stats["total"], 2)
        self.assertEqual(stats["counts"]["ALLOW"], 1)
        self.assertEqual(stats["counts"]["DENY"], 1)

    def test_missing_log_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = AtlassianTraceReader(Path(tmp) / "missing.jsonl").all()
        self.assertEqual(result, [])

    def test_malformed_line_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "log.jsonl"
            log_path.write_text('not json\n{"direction":"decision","timestamp":"t",'
                                '"trace_id":"x","tool":"t","decision":"ALLOW"}\n')
            entries = AtlassianTraceReader(log_path).all()
        self.assertEqual(len(entries), 1)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class TestAtlassianCLI(unittest.TestCase):
    def _write_log(self, tmp):
        log_path = Path(tmp) / "log.jsonl"
        entries = [
            {"direction": "decision", "timestamp": "2026-01-01T00:00:01Z",
             "trace_id": "aaaa-1234", "tool": "jira_get_issue", "decision": "ALLOW",
             "rule": "default_allow", "tainted": False, "flow_labels": []},
            {"direction": "decision", "timestamp": "2026-01-01T00:01:01Z",
             "trace_id": "bbbb-5678", "tool": "jira_create_issue", "decision": "DENY",
             "rule": "no_raw_confluence_to_jira", "tainted": False,
             "flow_labels": ["confluence_raw"]},
        ]
        with log_path.open("w") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")
        return log_path

    def test_list_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = self._write_log(tmp)
            with patch("sys.stdout", io.StringIO()) as out:
                rc = cli_main(["list", "--log", str(log_path)])
        self.assertEqual(rc, 0)
        output = out.getvalue()
        self.assertIn("jira_get_issue", output)
        self.assertIn("ALLOW", output)
        self.assertIn("DENY", output)

    def test_stats_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = self._write_log(tmp)
            with patch("sys.stdout", io.StringIO()) as out:
                rc = cli_main(["stats", "--log", str(log_path)])
        self.assertEqual(rc, 0)
        output = out.getvalue()
        self.assertIn("2", output)  # total

    def test_filter_by_decision(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = self._write_log(tmp)
            with patch("sys.stdout", io.StringIO()) as out:
                cli_main(["list", "--log", str(log_path), "--decision", "DENY"])
        output = out.getvalue()
        self.assertIn("jira_create_issue", output)
        self.assertNotIn("jira_get_issue", output)

    def test_trace_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = self._write_log(tmp)
            # Add request + response entries for trace aaaa-1234
            with log_path.open("a") as f:
                f.write(json.dumps({"direction": "request", "timestamp": "t",
                                    "trace_id": "aaaa-1234", "payload": {}}) + "\n")
            with patch("sys.stdout", io.StringIO()) as out:
                rc = cli_main(["trace", "--log", str(log_path), "--trace-id", "aaaa-1234"])
        self.assertEqual(rc, 0)
        output = out.getvalue()
        self.assertIn("aaaa-1234", output)

    def test_trace_command_missing_trace_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = self._write_log(tmp)
            rc = cli_main(["trace", "--log", str(log_path)])
        self.assertEqual(rc, 1)

    def test_empty_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "empty.jsonl"
            log_path.write_text("")
            with patch("sys.stdout", io.StringIO()) as out:
                rc = cli_main(["list", "--log", str(log_path)])
        self.assertEqual(rc, 0)
        self.assertIn("No entries", out.getvalue())


if __name__ == "__main__":
    unittest.main()
