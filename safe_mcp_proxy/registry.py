from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Optional

from safe_mcp_proxy.descriptor import compute_descriptor_hash


@dataclass
class Tool:
    name: str
    capability: str
    schema: Dict[str, Any]
    descriptor_hash: str
    side_effect_type: str
    handler: Callable[[Dict[str, Any]], Dict[str, Any]]


class ToolRegistry:
    def __init__(self, upstream_tools: Iterable[Tool], allowlist: Iterable[str]):
        self._allowlist = set(allowlist)
        self._all_tools: Dict[str, Tool] = {tool.name: tool for tool in upstream_tools}
        self._exposed_tools: Dict[str, Tool] = {
            name: tool for name, tool in self._all_tools.items() if name in self._allowlist
        }

    @classmethod
    def with_mock_tools(cls, allowlist: Iterable[str]) -> "ToolRegistry":
        def _read_file(payload: Dict[str, Any]) -> Dict[str, Any]:
            return {"ok": True, "content": f"mock-read:{payload.get('path', '')}"}

        def _list_repo(payload: Dict[str, Any]) -> Dict[str, Any]:
            return {"ok": True, "files": payload.get("files", ["README.md", "safe_mcp_proxy/main.py"])}

        def _send_email(payload: Dict[str, Any]) -> Dict[str, Any]:
            return {"ok": True, "sent_to": payload.get("to", "unknown@example.com")}

        tool_defs = [
            (
                "read_file", "read_file",
                {"type": "object", "properties": {"path": {"type": "string"}}},
                "read", _read_file,
            ),
            (
                "list_repo", "list_repo",
                {"type": "object", "properties": {}},
                "internal", _list_repo,
            ),
            (
                "send_email", "send_email",
                {"type": "object", "properties": {"to": {"type": "string"}, "body": {"type": "string"}}},
                "external", _send_email,
            ),
            (
                "dangerous_exec", "dangerous_exec",
                {"type": "object", "properties": {"cmd": {"type": "string"}}},
                "external", lambda payload: {"ok": True, "cmd": payload.get("cmd")},
            ),
        ]

        tools = [
            Tool(
                name=name,
                capability=capability,
                schema=schema,
                descriptor_hash=compute_descriptor_hash(schema),
                side_effect_type=side_effect_type,
                handler=handler,
            )
            for name, capability, schema, side_effect_type, handler in tool_defs
        ]
        return cls(upstream_tools=tools, allowlist=allowlist)

    def get_tool(self, tool_name: str) -> Optional[Tool]:
        return self._exposed_tools.get(tool_name)

    def execute_tool(self, tool_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        tool = self.get_tool(tool_name)
        if tool is None:
            raise KeyError(f"Tool '{tool_name}' is not exposed")
        return tool.handler(payload)
