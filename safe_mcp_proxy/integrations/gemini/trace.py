from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_TRACE_FILE = _REPO_ROOT / "data" / "traces" / "gemini_trace.jsonl"


class GeminiTraceLogger:
    """Append-only structured trace log for Gemini proxy executions.

    Writes one JSON line per pipeline stage to data/traces/gemini_trace.jsonl.
    Stages (in order): request → tool_call → intent (or absent) → policy → execution.

    The file is created lazily on first write; parent directories are created
    automatically. Consistent with audit.jsonl format used by executor.py.
    """

    def __init__(self, trace_path: Path = _DEFAULT_TRACE_FILE) -> None:
        self._path = trace_path

    def record(
        self,
        *,
        stage: str,
        tool: str,
        taint: bool = False,
        source_channel: str = "",
        **data: Any,
    ) -> None:
        """Append one trace entry for the given pipeline stage."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stage": stage,
            "tool": tool,
            "taint": taint,
            "source_channel": source_channel,
        }
        entry.update(data)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")

    @property
    def trace_path(self) -> Path:
        return self._path
