from __future__ import annotations

from safe_mcp_proxy.decision import Decision
from safe_mcp_proxy.executor import Executor
from safe_mcp_proxy.integrations.gemini_adapter import GeminiAdapter
from safe_mcp_proxy.integrations.gemini_policy_gate import GeminiPolicyGate
from safe_mcp_proxy.integrations.intent_ir import IntentIRError, IntentMapper
from safe_mcp_proxy.provenance import Provenance


class GeminiProxy:
    """Routes a Gemini function-call request through the executor pipeline.

    Request flow:
        GeminiAdapter.parse()      →  ToolCall
        IntentMapper.map()         →  IntentIR   (IntentIRError if unknown)
        GeminiPolicyGate.evaluate()→  ExecutionSpec
        executor.execute()         →  result + audit log  (ALLOW / ASK only)
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
            # Action is not registered anywhere in the system.
            result = {"decision": "ABSENT", "rule": "action_not_in_ontology", "result": None}
            return GeminiAdapter.format_response(tool_call.tool_name, result)

        spec = self._policy_gate.evaluate(intent, provenance)

        if spec.decision in (Decision.DENY, Decision.ABSENT):
            # Short-circuit: no execution, no audit (policy gate made the call).
            result = {"decision": spec.decision.value, "rule": spec.rule, "result": None}
            return GeminiAdapter.format_response(tool_call.tool_name, result)

        # ALLOW / ASK: delegate to executor which handles execution, ASK token
        # creation, and audit logging.
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
