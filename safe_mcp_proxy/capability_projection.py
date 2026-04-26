"""Capability projection engine — deterministic filtering of skill-backed capabilities.

Projects a world manifest's skill_capabilities into the subset visible to an agent
given its identity, workflow, execution mode, and approval state.

Same inputs always produce the same output (no randomness, no I/O).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Tuple

from safe_mcp_proxy.compiler import SkillCapabilityConfig
from safe_mcp_proxy.execution_mode import ExecutionMode


# ---------------------------------------------------------------------------
# Side-effect classification sets
# ---------------------------------------------------------------------------

# Capabilities with these side effects are hidden in read-only workflows.
_WRITE_SIDE_EFFECTS: FrozenSet[str] = frozenset({
    "write",
    "external_communication",
    "deployment",
})

# Background mode additionally blocks bounded_compute.
_BACKGROUND_BLOCKED: FrozenSet[str] = _WRITE_SIDE_EFFECTS | frozenset({"bounded_compute"})


# ---------------------------------------------------------------------------
# Context and result
# ---------------------------------------------------------------------------


@dataclass
class ProjectionContext:
    """Execution context used to compute the projected capability set."""
    identity: str
    workflow_id: str
    mode: ExecutionMode = ExecutionMode.INTERACTIVE
    trust_context: str = "default"
    # Capabilities whose approval has been recorded — removes the approval gate.
    approved_capabilities: FrozenSet[str] = field(default_factory=frozenset)


@dataclass
class ProjectionResult:
    """Result of a projection pass."""
    visible: List[SkillCapabilityConfig]
    # Each entry: (capability_name, denial_reason_code)
    hidden: List[Tuple[str, str]]


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


def _is_readonly_workflow(workflow_id: str) -> bool:
    """Convention: workflow ids starting with read_only / read-only are read-only."""
    normalised = workflow_id.lower().replace("-", "_")
    return normalised.startswith("read_only") or normalised.endswith("_ro")


class CapabilityProjectionEngine:
    """Projects skill_capabilities to agent-visible tools for a given context.

    Evaluation order (first matching rule wins):
      1. allowed == False                    → capability_not_allowed
      2. background + blocking side effect   → side_effect_restricted_in_background
      3. read-only workflow + write effect   → side_effect_not_allowed_in_workflow
      4. requires_approval + not approved    → approval_required
      5. (none)                              → visible
    """

    def project(
        self,
        skill_capabilities: Dict[str, SkillCapabilityConfig],
        context: ProjectionContext,
    ) -> ProjectionResult:
        visible: List[SkillCapabilityConfig] = []
        hidden: List[Tuple[str, str]] = []

        readonly = _is_readonly_workflow(context.workflow_id)
        background = context.mode == ExecutionMode.BACKGROUND

        for cap in skill_capabilities.values():
            reason = self._deny_reason(cap, context, readonly, background)
            if reason:
                hidden.append((cap.name, reason))
            else:
                visible.append(cap)

        return ProjectionResult(visible=visible, hidden=hidden)

    def _deny_reason(
        self,
        cap: SkillCapabilityConfig,
        context: ProjectionContext,
        readonly: bool,
        background: bool,
    ) -> str:
        if cap.allowed is False:
            return "capability_not_allowed"
        if background and cap.side_effect in _BACKGROUND_BLOCKED:
            return "side_effect_restricted_in_background"
        if readonly and cap.side_effect in _WRITE_SIDE_EFFECTS:
            return "side_effect_not_allowed_in_workflow"
        if cap.requires_approval and cap.name not in context.approved_capabilities:
            return "approval_required"
        return ""
