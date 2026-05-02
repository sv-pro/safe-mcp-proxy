from __future__ import annotations

from safe_mcp_proxy.decision import Decision
from safe_mcp_proxy.executor import Executor
from safe_mcp_proxy.integrations.gemini_adapter import GeminiAdapter
from safe_mcp_proxy.integrations.gemini_policy_gate import GeminiPolicyGate
from safe_mcp_proxy.integrations.intent_ir import IntentIRError, IntentMapper
from safe_mcp_proxy.provenance import Provenance

_ABSENCE_MESSAGE = "Action does not exist in this world"


class GeminiProxy:
    """Routes a Gemini function-call request through the executor pipeline.

    Request flow:
        GeminiAdapter.parse()       →  ToolCall
        IntentMapper.map()          →  IntentIR   (IntentIRError → ontological absence)
        GeminiPolicyGate.evaluate() →  ExecutionSpec
        executor.execute()          →  result + audit log  (ALLOW / ASK)
        executor.execute()          →  ABSENT result + audit log  (allowlist miss)
        short-circuit               →  DENY response (no execution, logged separately)
    """

    def __init__(self, executor: Executor) -> None:
        self._executor = executor
        self._mapper = IntentMapper(executor.registry)
        self._policy_gate = GeminiPolicyGate(executor)

    def execute(self, request: dict) -> dict:
        tool_call = GeminiAdapter.parse(request)
        source = tool_call.metadata.get("source_channel", "web")
        provenance = Provenance.from_source(source)

        try:
            intent = self._mapper.map(tool_call)
        except IntentIRError:
            # Action is completely unknown — not in any world's catalog.
            # Log the absence and return the canonical response.
            self._executor.record_absence(
                tool_name=tool_call.tool_name,
                rule="action_not_in_ontology",
                source_channel=provenance.source_channel,
                taint=provenance.tainted,
            )
            result = {
                "decision": "ABSENT",
                "rule": "action_not_in_ontology",
                "message": _ABSENCE_MESSAGE,
                "result": None,
            }
            return GeminiAdapter.format_response(tool_call.tool_name, result)

        spec = self._policy_gate.evaluate(intent, provenance)

        if spec.decision == Decision.DENY:
            # Policy violation: short-circuit without execution.
            # Audit logging for deny is handled in issue #95 (provenance & trace).
            result = {
                "decision": spec.decision.value,
                "rule": spec.rule,
                "message": f"Action blocked by policy: {spec.rule}",
                "result": None,
            }
            return GeminiAdapter.format_response(tool_call.tool_name, result)

        # ABSENT (allowlist miss), ALLOW, ASK: delegate to executor.
        # The executor handles execution, ASK token creation, and audit logging.
        result = self._executor.execute(intent.action, intent.parameters, provenance)
        return GeminiAdapter.format_response(tool_call.tool_name, result)

    def list_tools(self) -> dict:
        """Return the manifest-filtered tool surface in Gemini function-declaration format.

        Only tools in the world allowlist are visible — absent tools are not
        mentioned, consistent with the ABSENT principle.
        """
        tools = self._executor.registry.list_exposed()
        return {
            "tools": [
                {"name": tool.name, "parameters": tool.schema}
                for tool in tools
            ]
        }
