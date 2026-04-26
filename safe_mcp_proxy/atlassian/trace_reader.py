"""Read and filter Atlassian MCP request/decision traces from JSONL audit log."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class TraceEntry:
    direction: str          # "request" | "decision" | "response"
    timestamp: str
    trace_id: str
    payload: Dict[str, Any] = field(default_factory=dict)
    tool: Optional[str] = None
    decision: Optional[str] = None
    rule: Optional[str] = None
    tainted: bool = False
    flow_labels: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TraceEntry":
        return cls(
            direction=d.get("direction", ""),
            timestamp=d.get("timestamp", ""),
            trace_id=d.get("trace_id", ""),
            payload=d.get("payload", {}),
            tool=d.get("tool"),
            decision=d.get("decision"),
            rule=d.get("rule"),
            tainted=d.get("tainted", False),
            flow_labels=d.get("flow_labels", []),
        )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "direction": self.direction,
            "timestamp": self.timestamp,
            "trace_id": self.trace_id,
            "tool": self.tool,
            "decision": self.decision,
            "rule": self.rule,
            "tainted": self.tainted,
            "flow_labels": self.flow_labels,
        }


class AtlassianTraceReader:
    """Read-only interface over an Atlassian requests JSONL log file."""

    def __init__(self, log_path: Path) -> None:
        self._path = log_path

    # ------------------------------------------------------------------

    def all(self) -> List[TraceEntry]:
        if not self._path.exists():
            return []
        entries = []
        with self._path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        entries.append(TraceEntry.from_dict(json.loads(line)))
                    except (json.JSONDecodeError, KeyError):
                        continue
        return entries

    def decisions(self) -> List[TraceEntry]:
        return [e for e in self.all() if e.direction == "decision"]

    def by_trace(self, trace_id: str) -> List[TraceEntry]:
        return [e for e in self.all() if e.trace_id == trace_id]

    def filter(
        self,
        *,
        decision: Optional[str] = None,
        tool: Optional[str] = None,
        last: Optional[int] = None,
    ) -> List[TraceEntry]:
        entries = self.decisions()
        if decision:
            entries = [e for e in entries if e.decision == decision.upper()]
        if tool:
            entries = [e for e in entries if e.tool == tool]
        if last:
            entries = entries[-last:]
        return entries

    def stats(self) -> Dict[str, Any]:
        decisions = self.decisions()
        counts: Dict[str, int] = {}
        for e in decisions:
            counts[e.decision or "UNKNOWN"] = counts.get(e.decision or "UNKNOWN", 0) + 1
        return {"total": len(decisions), "counts": counts}
