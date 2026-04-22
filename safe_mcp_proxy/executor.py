import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from safe_mcp_proxy.descriptor import compute_descriptor_hash, descriptor_hash_valid
from safe_mcp_proxy.policy_engine import PolicyEngine
from safe_mcp_proxy.provenance import Provenance
from safe_mcp_proxy.registry import ToolRegistry
from safe_mcp_proxy.simulate import simulate_external_action

ABSENT_MESSAGE = "Action does not exist in this world"


class Executor:
    def __init__(
        self,
        registry: ToolRegistry,
        policy_engine: PolicyEngine,
        audit_log_path: str,
        simulate_external: bool = False,
    ):
        self.registry = registry
        self.policy_engine = policy_engine
        self.simulate_external = simulate_external
        self.audit_log_path = Path(audit_log_path)

    def execute(self, tool_name: str, payload: Dict[str, Any], provenance: Provenance) -> Dict[str, Any]:
        tool = self.registry.get_tool(tool_name)
        capability = tool.capability if tool else tool_name
        side_effect_type = tool.side_effect_type if tool else "unknown"
        descriptor_hash_ok = descriptor_hash_valid(tool.schema, tool.descriptor_hash) if tool else True
        descriptor_hash = compute_descriptor_hash(tool.schema) if tool else ""

        policy = self.policy_engine.decide(
            tool_name=tool_name,
            capability=capability,
            taint=provenance.tainted,
            side_effect_type=side_effect_type,
            descriptor_hash_valid=descriptor_hash_ok,
        )

        if policy.decision == "ALLOW":
            if self.simulate_external and tool and tool.side_effect_type == "external":
                response = simulate_external_action()
            else:
                response = self.registry.execute_tool(tool_name, payload)
        elif policy.decision == "DENY":
            response = {"error": "Denied by policy", "reason": policy.rule_hit}
        else:
            response = {"error": ABSENT_MESSAGE}

        self._audit(
            tool=tool_name,
            decision=policy.decision,
            rule=policy.rule_hit,
            taint=provenance.tainted,
            descriptor_hash=descriptor_hash,
            source_channel=provenance.source_channel,
        )
        return {"decision": policy.decision, "rule": policy.rule_hit, "result": response}

    def _audit(
        self,
        tool: str,
        decision: str,
        rule: str,
        taint: bool,
        descriptor_hash: str,
        source_channel: str,
    ) -> None:
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool": tool,
            "decision": decision,
            "rule": rule,
            "taint": taint,
            "descriptor_hash": descriptor_hash,
            "source_channel": source_channel,
        }
        with self.audit_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")
