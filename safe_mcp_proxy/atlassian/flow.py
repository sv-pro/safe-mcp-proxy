"""Data Flow Control (Provenance Lite) for the Atlassian MCP path.

Tracks which data labels are active in a session and enforces flow rules
(e.g. confluence_raw must not flow into an external write tool).

Labels assigned per tool output:
  confluence_raw     — raw confluence_get_page response (not abstracted)
  confluence_summary — safe-abstracted confluence_get_page response
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Set


# Data labels produced by Atlassian tool outputs.
LABEL_CONFLUENCE_RAW = "confluence_raw"
LABEL_CONFLUENCE_SUMMARY = "confluence_summary"

# Tools whose output produces a data label.
_OUTPUT_LABELS: Dict[str, str] = {
    "confluence_get_page": LABEL_CONFLUENCE_RAW,
}
# When the safe abstraction is applied, the label changes to summary.
_ABSTRACTION_LABEL: Dict[str, str] = {
    LABEL_CONFLUENCE_RAW: LABEL_CONFLUENCE_SUMMARY,
}


class FlowContext:
    """Mutable session-level tracker of active data labels.

    Updated after each tools/call response; consulted by the policy engine
    before the next tools/call to enforce data-flow rules.
    """

    def __init__(self) -> None:
        self._labels: Set[str] = set()

    # ------------------------------------------------------------------

    def tag_output(self, tool_name: str, was_abstracted: bool) -> None:
        """Record the data label produced by a successful tool output."""
        base_label = _OUTPUT_LABELS.get(tool_name)
        if base_label is None:
            return
        if was_abstracted:
            label = _ABSTRACTION_LABEL.get(base_label, base_label)
        else:
            label = base_label
        self._labels.add(label)

    def active_labels(self) -> Set[str]:
        return set(self._labels)

    def has_label(self, label: str) -> bool:
        return label in self._labels

    def clear(self) -> None:
        self._labels.clear()

    def as_dict(self) -> Dict[str, Any]:
        return {"active_labels": sorted(self._labels)}


@dataclass
class DataFlowRule:
    if_label: str
    deny_for: List[str]
    rule: str


def parse_data_flow_rules(raw: List[Dict[str, Any]]) -> List[DataFlowRule]:
    return [
        DataFlowRule(
            if_label=r["if_label"],
            deny_for=list(r.get("deny_for", [])),
            rule=r.get("rule", f"data_flow:{r['if_label']}"),
        )
        for r in raw
    ]
