from __future__ import annotations

from safe_mcp_proxy.executor import Executor
from safe_mcp_proxy.integrations.gemini_adapter import GeminiAdapter
from safe_mcp_proxy.provenance import Provenance


class GeminiProxy:
    """Routes a Gemini function-call request through the executor pipeline.

    Phase 1 passthrough: parses the request, picks a source channel from the
    request metadata (defaults to "web"), and delegates to the executor which
    handles policy enforcement and audit logging.
    """

    def __init__(self, executor: Executor) -> None:
        self._executor = executor

    def execute(self, request: dict) -> dict:
        tool_call = GeminiAdapter.parse(request)
        source = tool_call.metadata.get("source_channel", "web")
        provenance = Provenance.from_source(source)
        result = self._executor.execute(
            tool_call.tool_name, tool_call.arguments, provenance
        )
        return GeminiAdapter.format_response(tool_call.tool_name, result)
