import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from safe_mcp_proxy.approval_store import ApprovalStore
from safe_mcp_proxy.decision import Decision
from safe_mcp_proxy.descriptor import compute_descriptor_hash, descriptor_hash_valid
from safe_mcp_proxy.execution_mode import ExecutionMode
from safe_mcp_proxy.policy_engine import PolicyEngine
from safe_mcp_proxy.provenance import Provenance
from safe_mcp_proxy.registry import Tool, ToolRegistry
from safe_mcp_proxy.simulate import simulate_external_action

ABSENT_MESSAGE = "Action does not exist in this world"


class Executor:
    def __init__(
        self,
        registry: ToolRegistry,
        policy_engine: PolicyEngine,
        audit_log_path: str,
        simulate_external: bool = False,
        approval_store: Optional[ApprovalStore] = None,
    ):
        self.registry = registry
        self.policy_engine = policy_engine
        self.simulate_external = simulate_external
        self.audit_log_path = Path(audit_log_path)
        self.approval_store = approval_store or ApprovalStore()

    def _tool_context(self, tool_name: str) -> Tuple[Optional[Tool], str, str, bool]:
        tool = self.registry.get_tool(tool_name)
        capability = tool.capability if tool else tool_name
        side_effect_type = tool.side_effect_type if tool else "unknown"
        hash_ok = descriptor_hash_valid(tool.schema, tool.descriptor_hash) if tool else True
        return tool, capability, side_effect_type, hash_ok

    def execute(self, tool_name: str, payload: Dict[str, Any], provenance: Provenance) -> Dict[str, Any]:
        tool, capability, side_effect_type, hash_ok = self._tool_context(tool_name)
        descriptor_hash = compute_descriptor_hash(tool.schema) if tool else ""

        policy = self.policy_engine.decide(
            tool_name=tool_name,
            capability=capability,
            taint=provenance.tainted,
            side_effect_type=side_effect_type,
            descriptor_hash_valid=hash_ok,
        )

        if policy.decision == Decision.ALLOW:
            if self.simulate_external and tool and tool.side_effect_type == "external":
                response = simulate_external_action()
            else:
                response = self.registry.execute_tool(tool_name, payload)
            self._audit(
                tool=tool_name,
                decision=policy.decision.value,
                rule=policy.rule_hit,
                taint=provenance.tainted,
                descriptor_hash=descriptor_hash,
                source_channel=provenance.source_channel,
            )
            return {"decision": policy.decision.value, "rule": policy.rule_hit, "result": response}

        elif policy.decision == Decision.DENY:
            response = {"error": "Denied by policy", "reason": policy.rule_hit}
            self._audit(
                tool=tool_name,
                decision=policy.decision.value,
                rule=policy.rule_hit,
                taint=provenance.tainted,
                descriptor_hash=descriptor_hash,
                source_channel=provenance.source_channel,
            )
            return {"decision": policy.decision.value, "rule": policy.rule_hit, "result": response}

        elif policy.decision == Decision.ASK:
            if provenance.execution_mode == ExecutionMode.BACKGROUND:
                # Background mode cannot prompt for approval — fall back to DENY
                effective_rule = "ask_unavailable_in_background"
                response = {"error": "Denied by policy", "reason": effective_rule}
                self._audit(
                    tool=tool_name,
                    decision=Decision.DENY.value,
                    rule=effective_rule,
                    taint=provenance.tainted,
                    descriptor_hash=descriptor_hash,
                    source_channel=provenance.source_channel,
                )
                return {"decision": Decision.DENY.value, "rule": effective_rule, "result": response}
            else:
                # INTERACTIVE mode — create token and surface for approval
                token = self.approval_store.create(
                    tool_name=tool_name,
                    payload=payload,
                    source_channel=provenance.source_channel,
                    tainted=provenance.tainted,
                    execution_mode=provenance.execution_mode.value,
                )
                self._audit(
                    tool=tool_name,
                    decision=Decision.ASK.value,
                    rule=policy.rule_hit,
                    taint=provenance.tainted,
                    descriptor_hash=descriptor_hash,
                    source_channel=provenance.source_channel,
                )
                return {
                    "decision": Decision.ASK.value,
                    "rule": policy.rule_hit,
                    "approval_token": token,
                    "result": None,
                }

        else:
            # ABSENT
            response = {"error": ABSENT_MESSAGE}
            self._audit(
                tool=tool_name,
                decision=policy.decision.value,
                rule=policy.rule_hit,
                taint=provenance.tainted,
                descriptor_hash=descriptor_hash,
                source_channel=provenance.source_channel,
            )
            return {"decision": policy.decision.value, "rule": policy.rule_hit, "result": response}

    def execute_approved(self, token: str) -> Dict[str, Any]:
        """Execute a previously ASK'd tool after its approval token has been approved."""
        entry = self.approval_store.get(token)
        if entry is None:
            return {"error": "Token not found", "approval_token": token}
        if entry.status != "approved":
            return {"error": f"Token is {entry.status}, not approved", "approval_token": token}

        tool = self.registry.get_tool(entry.tool_name)
        descriptor_hash = compute_descriptor_hash(tool.schema) if tool else ""

        if tool is None:
            response = {"error": ABSENT_MESSAGE}
            decision_val, rule_val = Decision.ABSENT.value, "tool_not_allowlisted"
        elif self.simulate_external and tool.side_effect_type == "external":
            response = simulate_external_action()
            decision_val, rule_val = Decision.ALLOW.value, "approved"
        else:
            response = self.registry.execute_tool(entry.tool_name, entry.payload)
            decision_val, rule_val = Decision.ALLOW.value, "approved"

        self.approval_store.mark_executed(token)
        self._audit(
            tool=entry.tool_name,
            decision=decision_val,
            rule=rule_val,
            taint=entry.tainted,
            descriptor_hash=descriptor_hash,
            source_channel=entry.source_channel,
        )
        return {
            "decision": decision_val,
            "rule": rule_val,
            "approval_token": token,
            "result": response,
        }

    def reject_approval(self, token: str) -> Dict[str, Any]:
        """Record a rejection for a pending approval token."""
        entry = self.approval_store.get(token)
        if entry is None:
            return {"error": "Token not found", "approval_token": token}
        if entry.status != "pending":
            return {"error": f"Token is already {entry.status}", "approval_token": token}

        self.approval_store.reject(token)
        tool = self.registry.get_tool(entry.tool_name)
        descriptor_hash = compute_descriptor_hash(tool.schema) if tool else ""

        self._audit(
            tool=entry.tool_name,
            decision=Decision.DENY.value,
            rule="approval_rejected",
            taint=entry.tainted,
            descriptor_hash=descriptor_hash,
            source_channel=entry.source_channel,
        )
        return {
            "decision": Decision.DENY.value,
            "rule": "approval_rejected",
            "approval_token": token,
            "result": {"error": "Denied by policy", "reason": "approval_rejected"},
        }

    def replay(self, audit_entry: Dict[str, Any]) -> Dict[str, Any]:
        tool_name = audit_entry["tool"]
        tainted = audit_entry["taint"]

        _, capability, side_effect_type, hash_ok = self._tool_context(tool_name)

        policy = self.policy_engine.decide(
            tool_name=tool_name,
            capability=capability,
            taint=tainted,
            side_effect_type=side_effect_type,
            descriptor_hash_valid=hash_ok,
        )

        matches = policy.decision.value == audit_entry["decision"] and policy.rule_hit == audit_entry["rule"]
        return {
            "recorded_decision": audit_entry["decision"],
            "recorded_rule": audit_entry["rule"],
            "replayed_decision": policy.decision.value,
            "replayed_rule": policy.rule_hit,
            "matches": matches,
        }

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
