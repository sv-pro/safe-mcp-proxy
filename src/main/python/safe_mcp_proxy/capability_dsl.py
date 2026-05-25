"""Parameterized capability definitions — constrained forms over base tools.

A CapabilityDef binds a base tool's arguments to value sources:
  - LiteralSource   — value baked into the definition; actors cannot override it
  - ActorInputSource — value supplied by the actor at call time
  - ContextRefSource — value resolved from a named context key at call time (not yet wired)

The actor-visible schema contains only ActorInput args. Literal args are invisible
to the caller and are injected by the registry handler at execution time.

Ported from agent-hypervisor/src/agent_hypervisor/authoring/capabilities/.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Union


# ---------------------------------------------------------------------------
# Value sources
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LiteralSource:
    """Fixed value baked into the capability definition. Actors cannot override it."""
    value: str


@dataclass(frozen=True)
class ActorInputSource:
    """Value supplied by the actor at call time."""


@dataclass(frozen=True)
class ContextRefSource:
    """Value resolved from a named runtime context key. Not yet wired in safe-mcp-proxy."""
    ref: str


ValueSource = Union[LiteralSource, ActorInputSource, ContextRefSource]


# ---------------------------------------------------------------------------
# Capability argument and definition
# ---------------------------------------------------------------------------


@dataclass
class CapabilityArgDef:
    value_source: ValueSource


@dataclass
class CapabilityDef:
    """A constrained action form over a base tool."""
    name: str
    base_tool: str
    args: Dict[str, CapabilityArgDef]


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def parse_capability_definitions(raw: Dict[str, Any]) -> Dict[str, CapabilityDef]:
    """Parse the ``capability_definitions`` section of a world manifest dict."""
    if not isinstance(raw, dict):
        raise ValueError("'capability_definitions' must be a mapping")
    result: Dict[str, CapabilityDef] = {}
    for name, defn in raw.items():
        if not isinstance(defn, dict):
            raise ValueError(f"Capability {name!r}: definition must be a mapping")
        base_tool = defn.get("base_tool")
        if not base_tool:
            raise ValueError(f"Capability {name!r}: 'base_tool' is required")
        raw_args = defn.get("args", {})
        if not isinstance(raw_args, dict):
            raise ValueError(f"Capability {name!r}: 'args' must be a mapping")
        args: Dict[str, CapabilityArgDef] = {}
        for arg_name, arg_defn in raw_args.items():
            args[arg_name] = _parse_arg(name, arg_name, arg_defn)
        result[name] = CapabilityDef(name=name, base_tool=base_tool, args=args)
    return result


def _parse_arg(cap_name: str, arg_name: str, data: Any) -> CapabilityArgDef:
    if not isinstance(data, dict):
        raise ValueError(
            f"Capability {cap_name!r}, arg {arg_name!r}: definition must be a mapping"
        )
    value_from = data.get("valueFrom")
    if value_from is None:
        raise ValueError(
            f"Capability {cap_name!r}, arg {arg_name!r}: 'valueFrom' is required"
        )
    if not isinstance(value_from, dict):
        raise ValueError(
            f"Capability {cap_name!r}, arg {arg_name!r}: 'valueFrom' must be a mapping"
        )
    source = _parse_value_source(cap_name, arg_name, value_from)
    return CapabilityArgDef(value_source=source)


_KNOWN_SOURCES = frozenset({"literal", "actor_input", "context_ref"})


def _parse_value_source(cap_name: str, arg_name: str, data: Dict[str, Any]) -> ValueSource:
    keys = set(data.keys())
    unknown = keys - _KNOWN_SOURCES
    if unknown:
        raise ValueError(
            f"Capability {cap_name!r}, arg {arg_name!r}: "
            f"unknown source kind(s): {sorted(unknown)}. Supported: {sorted(_KNOWN_SOURCES)}"
        )
    if not keys:
        raise ValueError(
            f"Capability {cap_name!r}, arg {arg_name!r}: 'valueFrom' must specify a source kind"
        )
    if len(keys) > 1:
        raise ValueError(
            f"Capability {cap_name!r}, arg {arg_name!r}: "
            f"'valueFrom' must specify exactly one source kind, got: {sorted(keys)}"
        )
    kind = next(iter(keys))
    inner = data[kind]

    if kind == "literal":
        if not isinstance(inner, dict) or "value" not in inner:
            raise ValueError(
                f"Capability {cap_name!r}, arg {arg_name!r}: "
                f"'literal' source requires a 'value' field"
            )
        return LiteralSource(value=str(inner["value"]))

    if kind == "actor_input":
        return ActorInputSource()

    if kind == "context_ref":
        if not isinstance(inner, dict) or "ref" not in inner:
            raise ValueError(
                f"Capability {cap_name!r}, arg {arg_name!r}: "
                f"'context_ref' source requires a 'ref' field"
            )
        return ContextRefSource(ref=str(inner["ref"]))

    raise ValueError(f"Unexpected source kind: {kind!r}")  # unreachable
