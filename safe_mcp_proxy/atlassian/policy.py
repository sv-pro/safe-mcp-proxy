from __future__ import annotations

import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

from .flow import DataFlowRule, parse_data_flow_rules

if TYPE_CHECKING:
    from .flow import FlowContext


@dataclass(frozen=True)
class PolicyDecision:
    decision: str   # "ALLOW" | "DENY" | "ABSENT"
    rule: str
    tool: str
    tainted: bool


class ManifestPolicyEngine:
    """Deterministic policy engine for the Atlassian MCP path.

    Decision order (first match wins):
    1. ABSENT — tool not in allowlist
    2. DENY   — tainted source + external-write tool  (taint flow rule)
    3. DENY   — data-flow label rule violated          (provenance lite)
    4. DENY   — argument rule violated
    5. ALLOW  — default
    """

    def __init__(self, manifest: Dict[str, Any]) -> None:
        self._allowlist: Set[str] = set(manifest.get("allowed_tools", []))
        self._external_write: Set[str] = set(manifest.get("external_write_tools", []))
        self._arg_rules: Dict[str, List[Dict[str, Any]]] = manifest.get("arg_rules", {})
        flow = manifest.get("flow_rules", {})
        self._taint_blocks_external: bool = flow.get(
            "tainted_source_blocks_external_write", True
        )
        self._data_flow_rules: List[DataFlowRule] = parse_data_flow_rules(
            manifest.get("data_flow_rules", [])
        )

    # ------------------------------------------------------------------

    def evaluate(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        tainted: bool,
        flow_context: Optional["FlowContext"] = None,
    ) -> PolicyDecision:
        # 1. Tool not in allowlist → ABSENT
        if self._allowlist and tool_name not in self._allowlist:
            return PolicyDecision("ABSENT", "tool_not_allowlisted", tool_name, tainted)

        # 2. Tainted source + external write → DENY
        if self._taint_blocks_external and tainted and tool_name in self._external_write:
            return PolicyDecision(
                "DENY", "tainted_source_blocks_external_write", tool_name, tainted
            )

        # 3. Data-flow label rules (provenance lite)
        if flow_context is not None:
            for dfr in self._data_flow_rules:
                if flow_context.has_label(dfr.if_label) and tool_name in dfr.deny_for:
                    return PolicyDecision("DENY", dfr.rule, tool_name, tainted)

        # 4. Argument-based rules
        for rule in self._arg_rules.get(tool_name, []):
            arg_val = arguments.get(rule["arg"])
            allowed_values = rule.get("allowed_values")
            if allowed_values is not None and arg_val not in allowed_values:
                rule_name = rule.get("rule", f"arg_rule:{rule['arg']}")
                return PolicyDecision("DENY", rule_name, tool_name, tainted)

        # 5. Default allow
        return PolicyDecision("ALLOW", "default_allow", tool_name, tainted)

    # ------------------------------------------------------------------

    @classmethod
    def from_yaml(cls, path: Path) -> "ManifestPolicyEngine":
        with path.open(encoding="utf-8") as fh:
            manifest = yaml.safe_load(fh)
        return cls(manifest or {})
