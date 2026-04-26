"""Baseline agent runner — executes scenario steps directly with no policy enforcement.

Used to establish the attack-succeeds baseline for MCPZero Demo comparisons.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List

from attacks.loader import AttackScenario

_DEFAULT_HANDLERS: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    "read_file":  lambda p: {"ok": True, "content": f"mock-read:{p.get('path', '')}"},
    "list_repo":  lambda p: {"ok": True, "files": ["README.md", "config.yaml", "sensitive_data.txt"]},
    "send_email": lambda p: {"ok": True, "sent_to": p.get("to", "unknown@example.com")},
    "dangerous_exec": lambda p: {"ok": True, "cmd": p.get("cmd", "")},
}


class BaselineAgent:
    """Simulated agent with direct tool access — no proxy, no policy.

    Every step in a scenario is executed unconditionally.  This is the
    "attack succeeds" baseline used to show that the exploit would work
    without Safe MCP Proxy in path.
    """

    def __init__(self, handlers: Dict[str, Callable] | None = None) -> None:
        self._handlers = handlers or _DEFAULT_HANDLERS

    def run(self, scenario: AttackScenario) -> List[Dict[str, Any]]:
        """Execute all steps in the scenario and return per-step results."""
        results = []
        for step in scenario.steps:
            handler = self._handlers.get(step.tool)
            if handler is not None:
                outcome = handler(step.payload)
                results.append({
                    "tool":     step.tool,
                    "payload":  step.payload,
                    "decision": "ALLOW",
                    "rule":     "no_policy",
                    "result":   outcome,
                })
            else:
                results.append({
                    "tool":     step.tool,
                    "payload":  step.payload,
                    "decision": "ABSENT",
                    "rule":     "tool_unknown",
                    "result":   None,
                })
        return results
