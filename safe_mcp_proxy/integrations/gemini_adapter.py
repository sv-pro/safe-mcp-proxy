from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


class GeminiAdapterError(ValueError):
    """Raised when a Gemini request cannot be parsed."""

    def __init__(self, missing_field: str) -> None:
        self.field = missing_field
        super().__init__(f"Invalid Gemini request: missing or invalid field '{missing_field}'")


@dataclass
class ToolCall:
    """Normalised representation of a Gemini function call."""

    tool_name: str
    arguments: Dict[str, Any]
    session_id: Optional[str]
    agent_id: Optional[str]
    metadata: Dict[str, Any]
    raw_request: Dict[str, Any]


class GeminiAdapter:
    """Stateless adapter between Gemini function-call JSON and internal ToolCall."""

    @classmethod
    def parse(cls, request: Dict[str, Any]) -> ToolCall:
        """Convert a raw Gemini request dict to a ToolCall.

        Raises GeminiAdapterError if required fields are absent or malformed.
        Does not execute or validate against any policy.
        """
        if not isinstance(request, dict):
            raise GeminiAdapterError("request")

        function_call = request.get("functionCall")
        if function_call is None:
            raise GeminiAdapterError("functionCall")

        name = function_call.get("name")
        if not name:
            raise GeminiAdapterError("name")

        arguments: Dict[str, Any] = function_call.get("args") or {}

        raw_metadata: Dict[str, Any] = request.get("metadata") or {}
        session_id: Optional[str] = raw_metadata.get("session_id")
        agent_id: Optional[str] = raw_metadata.get("agent_id")

        return ToolCall(
            tool_name=name,
            arguments=arguments,
            session_id=session_id,
            agent_id=agent_id,
            metadata=raw_metadata,
            raw_request=request,
        )

    @classmethod
    def format_response(cls, tool_name: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Wrap a tool result in the Gemini functionResponse envelope."""
        return {"functionResponse": {"name": tool_name, "response": result}}
