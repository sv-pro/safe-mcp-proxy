from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from safe_mcp_proxy.integrations.gemini_adapter import ToolCall
from safe_mcp_proxy.registry import ToolRegistry


class IntentIRError(KeyError):
    """Raised when the requested action is not in the system ontology.

    Distinct from ABSENT (policy blocks a *known* action) — here the action
    is completely unknown: no tool record exists for it in the registry.
    """

    def __init__(self, action: str) -> None:
        self.action = action
        super().__init__(f"Action not in ontology: {action!r}")


@dataclass(frozen=True)
class IntentIR:
    """Strict intermediate representation of an agent's intent.

    Sits between adapter parsing (ToolCall) and policy evaluation (executor).
    All fields are resolved deterministically from the registry — no inference,
    no guessing, no fallback.
    """

    action: str
    parameters: Dict[str, Any]
    required_capabilities: List[str]
    side_effect_type: str
    descriptor_hash: str


class IntentMapper:
    """Maps a normalised ToolCall to an IntentIR using the tool registry.

    Uses the full tool catalog (not just the allowlist) to detect ontology
    membership. A tool that exists but is not allowlisted will still produce
    a valid IntentIR — the policy engine decides whether execution is ABSENT
    or ALLOW/DENY. A completely unknown tool raises IntentIRError.
    """

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    def map(self, tool_call: ToolCall) -> IntentIR:
        """Convert a ToolCall to an IntentIR.

        Raises:
            IntentIRError: if tool_call.tool_name is not registered anywhere
                in the system (not in the full catalog, allowlisted or not).
        """
        tool = self._registry.get_any_tool(tool_call.tool_name)
        if tool is None:
            raise IntentIRError(tool_call.tool_name)
        return IntentIR(
            action=tool_call.tool_name,
            parameters=tool_call.arguments,
            required_capabilities=[tool.capability],
            side_effect_type=tool.side_effect_type,
            descriptor_hash=tool.descriptor_hash,
        )
