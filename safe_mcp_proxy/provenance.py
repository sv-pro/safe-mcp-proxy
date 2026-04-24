from dataclasses import dataclass, field
from typing import Iterable, Tuple

from safe_mcp_proxy.execution_mode import ExecutionMode

TAINTED_CHANNELS = {"email", "web", "tool_output"}


@dataclass(frozen=True)
class Provenance:
    source_channel: str
    tainted: bool
    parent_sources: Tuple[str, ...] = field(default_factory=tuple)
    execution_mode: ExecutionMode = field(default=ExecutionMode.INTERACTIVE)

    @classmethod
    def from_source(
        cls,
        source_channel: str,
        parent_sources: Iterable[str] = (),
        execution_mode: ExecutionMode = ExecutionMode.INTERACTIVE,
    ) -> "Provenance":
        parents = tuple(parent_sources)
        tainted = source_channel in TAINTED_CHANNELS or any(parent in TAINTED_CHANNELS for parent in parents)
        return cls(
            source_channel=source_channel,
            tainted=tainted,
            parent_sources=parents,
            execution_mode=execution_mode,
        )

    def derive(self, source_channel: str) -> "Provenance":
        tainted = self.tainted or source_channel in TAINTED_CHANNELS
        parent_sources = self.parent_sources + (self.source_channel,)
        return Provenance(
            source_channel=source_channel,
            tainted=tainted,
            parent_sources=parent_sources,
            execution_mode=self.execution_mode,
        )
