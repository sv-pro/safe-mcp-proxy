"""Tests for TraceStore (DS0.1)."""

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from safe_mcp_proxy.decision import Decision
from safe_mcp_proxy.trace_store import SCHEMA_VERSION, TraceRecord, TraceStore


def _write_jsonl(path: Path, entries: list) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for entry in entries:
            fh.write(json.dumps(entry) + "\n")


SAMPLE_ENTRIES = [
    {
        "timestamp": "2026-04-22T07:00:00+00:00",
        "tool": "read_file",
        "decision": "ALLOW",
        "rule": "default_allow",
        "source_channel": "cli",
        "taint": False,
        "descriptor_hash": "aabbcc",
    },
    {
        "timestamp": "2026-04-22T08:00:00+00:00",
        "tool": "send_email",
        "decision": "DENY",
        "rule": "tainted_external_side_effect",
        "source_channel": "web",
        "taint": True,
        "descriptor_hash": "ddeeff",
    },
    {
        "timestamp": "2026-04-22T09:00:00+00:00",
        "tool": "dangerous_exec",
        "decision": "ABSENT",
        "rule": "tool_not_allowlisted",
        "source_channel": "cli",
        "taint": False,
        "descriptor_hash": "",
    },
    {
        "timestamp": "2026-04-22T10:00:00+00:00",
        "tool": "read_file",
        "decision": "DENY",
        "rule": "descriptor_drift",
        "source_channel": "cli",
        "taint": False,
        "descriptor_hash": "112233",
    },
]


class TestTraceRecord(unittest.TestCase):
    def test_from_raw_normalizes_fields(self):
        raw = SAMPLE_ENTRIES[0]
        rec = TraceRecord.from_raw(1, raw)
        self.assertEqual(rec.id, 1)
        self.assertEqual(rec.schema_version, SCHEMA_VERSION)
        self.assertEqual(rec.timestamp, raw["timestamp"])
        self.assertEqual(rec.tool_requested, raw["tool"])
        self.assertEqual(rec.decision, Decision.ALLOW)
        self.assertEqual(rec.rule_hit, raw["rule"])
        self.assertEqual(rec.source_channel, raw["source_channel"])
        self.assertEqual(rec.taint, raw["taint"])
        self.assertEqual(rec.descriptor_hash, raw["descriptor_hash"])
        self.assertIsNone(rec.input)

    def test_from_raw_missing_fields_default(self):
        rec = TraceRecord.from_raw(5, {})
        self.assertEqual(rec.id, 5)
        self.assertEqual(rec.tool_requested, "")
        self.assertEqual(rec.decision, "")
        self.assertEqual(rec.rule_hit, "")
        self.assertEqual(rec.taint, False)
        self.assertIsNone(rec.input)

    def test_as_dict_round_trips(self):
        raw = SAMPLE_ENTRIES[1]
        rec = TraceRecord.from_raw(2, raw)
        d = rec.as_dict()
        self.assertEqual(d["id"], 2)
        self.assertEqual(d["schema_version"], SCHEMA_VERSION)
        self.assertEqual(d["tool_requested"], raw["tool"])
        self.assertEqual(d["decision"], raw["decision"])
        self.assertIn("input", d)

    def test_from_raw_unknown_decision_preserved_as_string(self):
        raw = dict(SAMPLE_ENTRIES[0], decision="FUTURE")
        rec = TraceRecord.from_raw(1, raw)
        self.assertEqual(rec.decision, "FUTURE")

    def test_record_is_immutable(self):
        rec = TraceRecord.from_raw(1, SAMPLE_ENTRIES[0])
        with self.assertRaises((AttributeError, TypeError)):
            rec.decision = "ALLOW"  # type: ignore[misc]


class TestTraceStoreAll(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.log = self.tmp / "audit.jsonl"
        _write_jsonl(self.log, SAMPLE_ENTRIES)
        self.store = TraceStore(str(self.log))

    def test_all_returns_all_records(self):
        records = self.store.all()
        self.assertEqual(len(records), len(SAMPLE_ENTRIES))

    def test_all_preserves_order(self):
        records = self.store.all()
        self.assertEqual(records[0].tool_requested, "read_file")
        self.assertEqual(records[1].tool_requested, "send_email")
        self.assertEqual(records[2].tool_requested, "dangerous_exec")

    def test_ids_are_1_based(self):
        records = self.store.all()
        for i, rec in enumerate(records, start=1):
            self.assertEqual(rec.id, i)

    def test_all_on_missing_file_returns_empty(self):
        store = TraceStore(str(self.tmp / "nonexistent.jsonl"))
        self.assertEqual(store.all(), [])

    def test_all_skips_blank_lines(self):
        content = "\n".join(json.dumps(e) for e in SAMPLE_ENTRIES[:2])
        content = "\n" + content + "\n\n"
        self.log.write_text(content, encoding="utf-8")
        records = self.store.all()
        self.assertEqual(len(records), 2)

    def test_all_skips_invalid_json(self):
        with self.log.open("a") as fh:
            fh.write("not valid json\n")
        records = self.store.all()
        self.assertEqual(len(records), len(SAMPLE_ENTRIES))


class TestTraceStoreLast(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.log = self.tmp / "audit.jsonl"
        _write_jsonl(self.log, SAMPLE_ENTRIES)
        self.store = TraceStore(str(self.log))

    def test_last_n_returns_n_records(self):
        records = self.store.last(2)
        self.assertEqual(len(records), 2)

    def test_last_n_returns_most_recent(self):
        records = self.store.last(2)
        self.assertEqual(records[-1].tool_requested, "read_file")  # last entry
        self.assertEqual(records[0].tool_requested, "dangerous_exec")

    def test_last_exceeding_total_returns_all(self):
        records = self.store.last(999)
        self.assertEqual(len(records), len(SAMPLE_ENTRIES))

    def test_last_zero_returns_empty(self):
        records = self.store.last(0)
        self.assertEqual(records, [])


class TestTraceStoreFilter(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.log = self.tmp / "audit.jsonl"
        _write_jsonl(self.log, SAMPLE_ENTRIES)
        self.store = TraceStore(str(self.log))

    def test_filter_by_decision_allow(self):
        records = self.store.filter(decision="ALLOW")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].decision, Decision.ALLOW)

    def test_filter_by_decision_deny(self):
        records = self.store.filter(decision="DENY")
        self.assertEqual(len(records), 2)
        for r in records:
            self.assertEqual(r.decision, Decision.DENY)

    def test_filter_by_decision_absent(self):
        records = self.store.filter(decision="ABSENT")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].tool_requested, "dangerous_exec")

    def test_filter_by_tool(self):
        records = self.store.filter(tool="read_file")
        self.assertEqual(len(records), 2)
        for r in records:
            self.assertEqual(r.tool_requested, "read_file")

    def test_filter_by_tool_and_decision(self):
        records = self.store.filter(tool="read_file", decision="ALLOW")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].decision, Decision.ALLOW)

    def test_filter_accepts_decision_enum(self):
        records = self.store.filter(decision=Decision.ABSENT)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].tool_requested, "dangerous_exec")

    def test_filter_by_since(self):
        since = datetime(2026, 4, 22, 8, 30, tzinfo=timezone.utc)
        records = self.store.filter(since=since)
        # entries at 09:00 and 10:00 qualify
        self.assertEqual(len(records), 2)
        for r in records:
            self.assertGreaterEqual(r.timestamp, "2026-04-22T09:00")

    def test_filter_by_until(self):
        until = datetime(2026, 4, 22, 8, 30, tzinfo=timezone.utc)
        records = self.store.filter(until=until)
        # entries at 07:00 and 08:00 qualify
        self.assertEqual(len(records), 2)

    def test_filter_by_since_and_until(self):
        since = datetime(2026, 4, 22, 8, 0, tzinfo=timezone.utc)
        until = datetime(2026, 4, 22, 9, 0, tzinfo=timezone.utc)
        records = self.store.filter(since=since, until=until)
        self.assertEqual(len(records), 2)

    def test_filter_no_criteria_returns_all(self):
        records = self.store.filter()
        self.assertEqual(len(records), len(SAMPLE_ENTRIES))

    def test_filter_unmatched_returns_empty(self):
        records = self.store.filter(decision="SIMULATE")
        self.assertEqual(records, [])

    def test_filter_unknown_tool_returns_empty(self):
        records = self.store.filter(tool="no_such_tool")
        self.assertEqual(records, [])

    def test_filter_against_real_audit_log(self):
        """Integration smoke: read the real audit.jsonl that ships with the repo."""
        import safe_mcp_proxy
        real_log = Path(safe_mcp_proxy.__file__).parent / "logs" / "audit.jsonl"
        if not real_log.exists():
            self.skipTest("real audit.jsonl not present")
        store = TraceStore(str(real_log))
        records = store.all()
        self.assertGreater(len(records), 0)
        for rec in records:
            self.assertIn(
                rec.decision.value if isinstance(rec.decision, Decision) else rec.decision,
                {"ALLOW", "DENY", "ABSENT", "SIMULATE", ""},
            )
            self.assertEqual(rec.schema_version, SCHEMA_VERSION)


if __name__ == "__main__":
    unittest.main()
