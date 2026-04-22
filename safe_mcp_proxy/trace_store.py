"""TraceStore — read-only, queryable view over the append-only audit JSONL log.

Stable record format (schema_version=1):
    id              — 1-based line number within the file
    schema_version  — int, always 1 for this format
    timestamp       — ISO-8601 UTC string (from audit entry)
    tool_requested  — tool name (audit field: "tool")
    decision        — ALLOW | DENY | ABSENT | SIMULATE
    rule_hit        — rule name (audit field: "rule")
    source_channel  — cli | web | email | tool_output
    taint           — bool
    descriptor_hash — SHA-256 hex string (empty string when absent)
    input           — dict | None  (not yet captured by executor; reserved)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class TraceRecord:
    id: int
    schema_version: int
    timestamp: str
    tool_requested: str
    decision: str
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
            "decision": self.decision,
            "rule_hit": self.rule_hit,
            "source_channel": self.source_channel,
            "taint": self.taint,
            "descriptor_hash": self.descriptor_hash,
            "input": self.input,
        }

    @staticmethod
    def from_raw(line_number: int, raw: dict) -> "TraceRecord":
        """Normalize one raw audit-log dict into a TraceRecord."""
        return TraceRecord(
            id=line_number,
            schema_version=SCHEMA_VERSION,
            timestamp=raw.get("timestamp", ""),
            tool_requested=raw.get("tool", ""),
            decision=raw.get("decision", ""),
            rule_hit=raw.get("rule", ""),
            source_channel=raw.get("source_channel", ""),
            taint=bool(raw.get("taint", False)),
            descriptor_hash=raw.get("descriptor_hash", ""),
            input=raw.get("input"),
        )


def _parse_timestamp(ts: str) -> Optional[datetime]:
    """Parse an ISO-8601 timestamp into an aware UTC datetime, or None on failure."""
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

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def all(self) -> List[TraceRecord]:
        """Return every record in chronological order."""
        return list(self._iter_records())

    def last(self, n: int) -> List[TraceRecord]:
        """Return the last *n* records (most-recent last)."""
        if n <= 0:
            return []
        records = self.all()
        return records[-n:] if n < len(records) else records

    def filter(
        self,
        *,
        decision: Optional[str] = None,
        tool: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> List[TraceRecord]:
        """Return records matching every supplied criterion.

        Args:
            decision: exact match on the ``decision`` field (ALLOW/DENY/ABSENT/SIMULATE).
            tool:     exact match on ``tool_requested``.
            since:    include only records with timestamp >= since (tz-aware datetime).
            until:    include only records with timestamp <= until (tz-aware datetime).
        """
        results = []
        for rec in self._iter_records():
            if decision is not None and rec.decision != decision:
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

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _iter_records(self):
        """Yield TraceRecord objects line by line from the JSONL file."""
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
