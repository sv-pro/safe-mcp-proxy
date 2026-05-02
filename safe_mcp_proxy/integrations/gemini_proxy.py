from __future__ import annotations

from safe_mcp_proxy.executor import Executor
from safe_mcp_proxy.integrations.gemini_adapter import GeminiAdapter
from safe_mcp_proxy.integrations.intent_ir import IntentIRError, IntentMapper
from safe_mcp_proxy.provenance import Provenance


class GeminiProxy:
    """Routes a Gemini function-call request through the executor pipeline.

    Request flow:
        GeminiAdapter.parse()  →  ToolCall
        IntentMapper.map()     →  IntentIR  (raises IntentIRError if unknown)
        executor.execute()     →  policy decision + audit log
        GeminiAdapter.format_response()  →  Gemini envelope
    """

    def __init__(self, executor: Executor) -> None:
        self._executor = executor
        self._mapper = IntentMapper(executor.registry)

    def execute(self, request: dict) -> dict:
        tool_call = GeminiAdapter.parse(request)
        source = tool_call.metadata.get("source_channel", "web")
        provenance = Provenance.from_source(source)

        try:
            intent = self._mapper.map(tool_call)
        except IntentIRError:
            # Action is not registered anywhere in the system — ontological absence.
            # Return a structured ABSENT response without touching the executor.
            result = {"decision": "ABSENT", "rule": "action_not_in_ontology", "result": None}
            return GeminiAdapter.format_response(tool_call.tool_name, result)

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
