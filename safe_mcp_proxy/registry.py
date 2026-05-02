from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Optional

from safe_mcp_proxy.capability_dsl import ActorInputSource, CapabilityDef, ContextRefSource, LiteralSource
from safe_mcp_proxy.descriptor import compute_descriptor_hash


@dataclass
class Tool:
    name: str
    capability: str
    schema: Dict[str, Any]
    descriptor_hash: str
    side_effect_type: str
    handler: Callable[[Dict[str, Any]], Dict[str, Any]]


def _build_scoped_tool(cap_def: CapabilityDef, base_tools: Dict[str, "Tool"]) -> "Tool":
    """Build a synthetic Tool from a CapabilityDef.

    The returned tool's schema exposes only actor_input args.
    Literal args are silently injected into every call; the actor cannot see or
    override them even if they include the key in their payload.
    """
    base = base_tools.get(cap_def.base_tool)
    if base is None:
        raise ValueError(
            f"Capability {cap_def.name!r}: base tool {cap_def.base_tool!r} not found in registry"
        )

    base_props = base.schema.get("properties", {})

    # Actor-visible schema: only actor_input args, types inherited from base schema.
    scoped_props = {
        arg_name: base_props.get(arg_name, {"type": "string"})
        for arg_name, arg_def in cap_def.args.items()
        if isinstance(arg_def.value_source, ActorInputSource)
    }
    scoped_schema = {"type": "object", "properties": scoped_props}

    # Literal injection map — these values are always applied, overriding any actor-supplied key.
    literals: Dict[str, str] = {
        arg_name: arg_def.value_source.value
        for arg_name, arg_def in cap_def.args.items()
        if isinstance(arg_def.value_source, LiteralSource)
    }

    # Validate no context_ref args (not yet wired).
    for arg_name, arg_def in cap_def.args.items():
        if isinstance(arg_def.value_source, ContextRefSource):
            raise NotImplementedError(
                f"Capability {cap_def.name!r}, arg {arg_name!r}: "
                f"ContextRefSource is not yet supported in safe-mcp-proxy"
            )

    actor_args = frozenset(
        arg_name for arg_name, arg_def in cap_def.args.items()
        if isinstance(arg_def.value_source, ActorInputSource)
    )
    base_handler = base.handler

    def scoped_handler(
        payload: Dict[str, Any],
        _actor_args: frozenset = actor_args,
        _literals: Dict[str, str] = literals,
        _base: Callable = base_handler,
    ) -> Dict[str, Any]:
        # Only pass through declared actor_input args, then inject literals.
        # This prevents the actor from sneaking locked args into the base call.
        filtered = {k: v for k, v in payload.items() if k in _actor_args}
        return _base({**filtered, **_literals})

    return Tool(
        name=cap_def.name,
        capability=cap_def.name,
        schema=scoped_schema,
        descriptor_hash=compute_descriptor_hash(scoped_schema),
        side_effect_type=base.side_effect_type,
        handler=scoped_handler,
    )


class ToolRegistry:
    def __init__(self, upstream_tools: Iterable[Tool], allowlist: Iterable[str]):
        self._allowlist = set(allowlist)
        self._all_tools: Dict[str, Tool] = {tool.name: tool for tool in upstream_tools}
        self._exposed_tools: Dict[str, Tool] = {
            name: tool for name, tool in self._all_tools.items() if name in self._allowlist
        }

    @classmethod
    def with_mock_tools(
        cls,
        allowlist: Iterable[str],
        capability_defs: Optional[Dict[str, CapabilityDef]] = None,
    ) -> "ToolRegistry":
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

        if capability_defs:
            base_by_name = {t.name: t for t in tools}
            for cap_def in capability_defs.values():
                tools.append(_build_scoped_tool(cap_def, base_by_name))

        return cls(upstream_tools=tools, allowlist=allowlist)

    def list_exposed(self) -> list[Tool]:
        """Return all tools visible in this world (allowlist-filtered)."""
        return list(self._exposed_tools.values())

    def get_any_tool(self, tool_name: str) -> Optional[Tool]:
        """Look up a tool from the full catalog regardless of allowlist.

        Used by IntentMapper to distinguish 'not in ontology' (unknown tool)
        from 'in ontology but absent in this world' (policy decision).
        """
        return self._all_tools.get(tool_name)

    def get_tool(self, tool_name: str) -> Optional[Tool]:
        return self._exposed_tools.get(tool_name)

    def execute_tool(self, tool_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        tool = self.get_tool(tool_name)
        if tool is None:
            raise KeyError(f"Tool '{tool_name}' is not exposed")
        return tool.handler(payload)
