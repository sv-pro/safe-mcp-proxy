"""Execution observer — records every tool call and decision to a JSONL trace file."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

TRACES_DIR = Path(__file__).parent.parent / "traces"


class ExecutionObserver:
    """Append-only trace logger for a single MCPZero demo run.

    One instance covers both the baseline and protected passes of a run so that
    the full side-by-side trace lives in one file.
    """

    def __init__(self, trace_dir: Path = TRACES_DIR) -> None:
        trace_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self._path = trace_dir / f"run_{ts}.jsonl"
        self._entries: List[Dict[str, Any]] = []

    def record(
        self,
        *,
        mode: str,
        scenario: str,
        tool: str,
        payload: Dict[str, Any],
        decision: str,
        rule: str | None = None,
        result: Any = None,
    ) -> None:
        entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mode":      mode,
            "scenario":  scenario,
            "tool":      tool,
            "payload":   payload,
            "decision":  decision,
        }
        if rule:
            entry["rule"] = rule
        if result is not None:
            entry["result"] = result

        self._entries.append(entry)
        with open(self._path, "a") as fh:
            fh.write(json.dumps(entry) + "\n")

    @property
    def entries(self) -> List[Dict[str, Any]]:
        return list(self._entries)

    @property
    def log_path(self) -> Path:
        return self._path
