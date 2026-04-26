"""Safe MCP Proxy enforcement layer for the MCPZero Demo.

Wraps `safe_mcp_proxy.main.build_executor` so every tool call is evaluated
against the mcpzero_demo world manifest before execution.  Tainted external
side effects are blocked deterministically — not by model behaviour.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from attacks.loader import AttackScenario
from safe_mcp_proxy.main import build_executor
from safe_mcp_proxy.provenance import Provenance

_REPO_ROOT = Path(__file__).resolve().parents[2]
_WORLD_ID = "mcpzero_demo"


class SafeMCPProxy:
    """Routes tool calls through the safe_mcp_proxy policy engine.

    Initialised once per run; honours the mcpzero_demo world manifest which
    allows send_email in the tool list but blocks it when provenance is tainted.
    """

    def __init__(self, world_id: str = _WORLD_ID, base_dir: Path = _REPO_ROOT) -> None:
        self._executor = build_executor(base_dir, world_id=world_id)

    def call(
        self,
        tool: str,
        payload: Dict[str, Any],
        source_channel: str,
    ) -> Dict[str, Any]:
        """Evaluate one tool call and return a normalised result dict."""
        provenance = Provenance.from_source(source_channel)
        raw = self._executor.execute(tool, payload, provenance)
        return {
            "tool":     tool,
            "payload":  payload,
            "decision": raw["decision"],
            "rule":     raw.get("rule"),
            "result":   raw.get("result"),
        }

    def run(self, scenario: AttackScenario) -> List[Dict[str, Any]]:
        """Execute all steps in a scenario through the proxy and return per-step results.

        For mcp_poison scenarios the tampered schema is applied to the registry
        before execution so that descriptor drift is triggered correctly.
        """
        if scenario.type == "mcp_poison" and scenario.poison_tool:
            self._apply_poison(scenario.poison_tool)

        results = []
        for step in scenario.steps:
            results.append(
                self.call(step.tool, step.payload, scenario.source_channel)
            )
        return results

    def _apply_poison(self, poison_tool: Dict[str, Any]) -> None:
        """Mutate a tool's schema in the registry to simulate descriptor drift."""
        name = poison_tool.get("name")
        tampered = poison_tool.get("tampered_schema")
        if not name or not tampered:
            return
        tool = self._executor.registry.get_tool(name)
        if tool is None:
            return
        tool.schema.clear()
        tool.schema.update(tampered)
