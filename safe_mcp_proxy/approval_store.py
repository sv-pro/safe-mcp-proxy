from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class PendingApproval:
    token: str
    tool_name: str
    payload: Dict[str, Any]
    source_channel: str
    tainted: bool
    execution_mode: str  # stored as plain str to avoid circular imports
    created_at: str
    status: str = "pending"  # "pending" | "approved" | "rejected"


class ApprovalStore:
    """In-memory store for pending approval tokens.

    Tokens are UUIDs. Each maps to a PendingApproval carrying the original
    tool name, payload, and provenance context needed for re-execution after
    the human approves.
    """

    def __init__(self) -> None:
        self._pending: Dict[str, PendingApproval] = {}

    def create(
        self,
        tool_name: str,
        payload: Dict[str, Any],
        source_channel: str,
        tainted: bool,
        execution_mode: str,
    ) -> str:
        token = str(uuid.uuid4())
        self._pending[token] = PendingApproval(
            token=token,
            tool_name=tool_name,
            payload=payload,
            source_channel=source_channel,
            tainted=tainted,
            execution_mode=execution_mode,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        return token

    def get(self, token: str) -> Optional[PendingApproval]:
        return self._pending.get(token)

    def approve(self, token: str) -> bool:
        entry = self._pending.get(token)
        if entry is None or entry.status != "pending":
            return False
        entry.status = "approved"
        return True

    def reject(self, token: str) -> bool:
        entry = self._pending.get(token)
        if entry is None or entry.status != "pending":
            return False
        entry.status = "rejected"
        return True

    def mark_executed(self, token: str) -> bool:
        entry = self._pending.get(token)
        if entry is None or entry.status != "approved":
            return False
        entry.status = "executed"
        return True
