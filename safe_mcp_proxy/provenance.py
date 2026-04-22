from dataclasses import dataclass, field
from typing import Iterable, Tuple

TAINTED_CHANNELS = {"email", "web", "tool_output"}


@dataclass(frozen=True)
class Provenance:
    source_channel: str
    tainted: bool
    parent_sources: Tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def from_source(cls, source_channel: str, parent_sources: Iterable[str] = ()) -> "Provenance":
        parents = tuple(parent_sources)
        tainted = source_channel in TAINTED_CHANNELS or any(parent in TAINTED_CHANNELS for parent in parents)
        return cls(source_channel=source_channel, tainted=tainted, parent_sources=parents)

    def derive(self, source_channel: str) -> "Provenance":
        tainted = self.tainted or source_channel in TAINTED_CHANNELS
        parent_sources = self.parent_sources + (self.source_channel,)
        return Provenance(source_channel=source_channel, tainted=tainted, parent_sources=parent_sources)
