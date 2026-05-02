from __future__ import annotations

from safe_mcp_proxy.descriptor import descriptor_hash_valid
from safe_mcp_proxy.executor import Executor
from safe_mcp_proxy.integrations.execution_spec import ExecutionSpec
from safe_mcp_proxy.integrations.intent_ir import IntentIR
from safe_mcp_proxy.provenance import Provenance


class GeminiPolicyGate:
    """Evaluates an IntentIR against the world manifest policy and returns an ExecutionSpec.

    Reuses the executor's PolicyEngine and registry — no logic is duplicated.
    Descriptor drift is detected by comparing the current schema hash against
    the hash recorded at registration time.

    This stage sits between IntentMapper (Issue #90) and execution routing
    (Issue #93). Its output, ExecutionSpec, carries the decision and all
    context needed for routing.
    """

    def __init__(self, executor: Executor) -> None:
        self._policy = executor.policy_engine
        self._registry = executor.registry

    def evaluate(self, intent: IntentIR, provenance: Provenance) -> ExecutionSpec:
        """Run policy evaluation for intent and return a typed ExecutionSpec.

        Uses the allowlist-filtered registry (get_tool) so that non-allowlisted
        tools are correctly caught by the tool_not_allowlisted rule.
        """
        tool = self._registry.get_tool(intent.action)
        hash_ok = (
            descriptor_hash_valid(tool.schema, tool.descriptor_hash)
            if tool is not None
            else True
        )
        capability = (
            intent.required_capabilities[0]
            if intent.required_capabilities
            else intent.action
        )

        policy_result = self._policy.decide(
            tool_name=intent.action,
            capability=capability,
            taint=provenance.tainted,
            side_effect_type=intent.side_effect_type,
            descriptor_hash_valid=hash_ok,
        )

        return ExecutionSpec(
            decision=policy_result.decision,
            rule=policy_result.rule_hit,
            intent=intent,
            provenance=provenance,
        )
