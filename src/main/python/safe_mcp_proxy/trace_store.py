from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Union

from safe_mcp_proxy.decision import Decision

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class TraceRecord:
    id: int
    schema_version: int
    timestamp: str
    tool_requested: str
    decision: Union[Decision, str]
    rule_hit: str
    source_channel: str
    taint: bool
    descriptor_hash: str
    input: Optional[dict] = field(default=None)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "schema_version": self.schema_version,
            "timestamp": self.timestamp,
            "tool_requested": self.tool_requested,
            "decision": self.decision.value if isinstance(self.decision, Decision) else self.decision,
            "rule_hit": self.rule_hit,
            "source_channel": self.source_channel,
            "taint": self.taint,
            "descriptor_hash": self.descriptor_hash,
            "input": self.input,
        }

    @staticmethod
    def from_raw(line_number: int, raw: dict) -> "TraceRecord":
        return TraceRecord(
            id=line_number,
            schema_version=SCHEMA_VERSION,
            timestamp=raw.get("timestamp", ""),
            tool_requested=raw.get("tool", ""),
            decision=Decision.parse(raw.get("decision", "")),
            rule_hit=raw.get("rule", ""),
            source_channel=raw.get("source_channel", ""),
            taint=bool(raw.get("taint", False)),
            descriptor_hash=raw.get("descriptor_hash", ""),
            input=raw.get("input"),
        )


def _parse_timestamp(ts: str) -> Optional[datetime]:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


class TraceStore:
    """Read-only store that streams and filters the audit JSONL log."""

    def __init__(self, audit_log_path: str) -> None:
        self._path = Path(audit_log_path)

    def all(self) -> List[TraceRecord]:
        return list(self._iter_records())

    def last(self, n: int) -> List[TraceRecord]:
        if n <= 0:
            return []
        records = self.all()
        return records[-n:] if n < len(records) else records

    def filter(
        self,
        *,
        decision: Optional[Union[Decision, str]] = None,
        tool: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> List[TraceRecord]:
        """Return records matching every supplied criterion (keyword-only)."""
        results = []
        expected_decision = Decision.parse(decision) if isinstance(decision, str) else decision
        for rec in self._iter_records():
            if expected_decision is not None and rec.decision != expected_decision:
                continue
            if tool is not None and rec.tool_requested != tool:
                continue
            if since is not None or until is not None:
                ts = _parse_timestamp(rec.timestamp)
                if ts is None:
                    continue
                if since is not None and ts < since:
                    continue
                if until is not None and ts > until:
                    continue
            results.append(rec)
        return results

    def _iter_records(self):
        if not self._path.exists():
            return
        with self._path.open(encoding="utf-8") as fh:
            for line_number, line in enumerate(fh, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    raw = json.loads(line)
                except json.JSONDecodeError:
                    continue
                yield TraceRecord.from_raw(line_number, raw)
