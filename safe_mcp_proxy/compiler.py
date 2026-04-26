from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Union

import yaml

from safe_mcp_proxy.capability_dsl import parse_capability_definitions


@dataclass
class SkillSourceConfig:
    """Parsed skill source entry from the world manifest."""
    name: str
    source_type: str            # "local" | "git"
    url: Optional[str] = None
    path: Optional[str] = None
    trust_level: str = "external_unverified"
    import_mode: str = "explicit_only"


@dataclass
class SkillCapabilityConfig:
    """A capability backed by an imported skill."""
    name: str
    source_skill: str           # "<source_name>:<skill_name>"
    exposed_as: str             # name visible to the agent
    allowed: Union[bool, str]   # True | False | "conditional"
    side_effect: str            # "none" | "bounded_compute" | "external_communication" | ...
    requires_approval: bool = False
    constraints: Dict[str, Any] = field(default_factory=dict)
    provenance_required: Optional[str] = None  # e.g. "trusted_or_user_confirmed"
    reason: Optional[str] = None               # human note when allowed=False


def parse_skill_sources(raw: Dict[str, Any]) -> Dict[str, SkillSourceConfig]:
    """Parse the ``skill_sources`` block from a raw world manifest dict."""
    result: Dict[str, SkillSourceConfig] = {}
    for name, cfg in raw.items():
        if not isinstance(cfg, dict):
            raise ValueError(f"skill_sources[{name!r}]: must be a mapping")
        source_type = cfg.get("type", "local")
        result[name] = SkillSourceConfig(
            name=name,
            source_type=source_type,
            url=cfg.get("url"),
            path=cfg.get("path"),
            trust_level=cfg.get("trust_level", "external_unverified"),
            import_mode=cfg.get("import_mode", "explicit_only"),
        )
    return result


def parse_skill_capabilities(
    raw_capabilities: Dict[str, Any],
    skill_sources: Dict[str, SkillSourceConfig],
) -> Dict[str, SkillCapabilityConfig]:
    """Parse skill-backed capability entries from the ``capabilities`` block.

    An entry is considered skill-backed when it contains a ``source_skill`` key.
    Non-skill-backed entries are ignored here (handled by the existing compiler path).

    Raises ValueError if ``source_skill`` references an undeclared source.
    """
    result: Dict[str, SkillCapabilityConfig] = {}
    for cap_name, cfg in raw_capabilities.items():
        if not isinstance(cfg, dict):
            continue
        source_skill = cfg.get("source_skill")
        if source_skill is None:
            continue
        # Validate source reference
        source_name = source_skill.split(":")[0]
        if source_name not in skill_sources:
            raise ValueError(
                f"capabilities[{cap_name!r}]: source_skill references unknown source "
                f"{source_name!r}. Declare it under skill_sources first."
            )
        allowed_raw = cfg.get("allowed", False)
        if isinstance(allowed_raw, str):
            allowed: Union[bool, str] = allowed_raw  # "conditional"
        else:
            allowed = bool(allowed_raw)

        result[cap_name] = SkillCapabilityConfig(
            name=cap_name,
            source_skill=source_skill,
            exposed_as=cfg.get("exposed_as", cap_name),
            allowed=allowed,
            side_effect=cfg.get("side_effect", "none"),
            requires_approval=bool(cfg.get("requires_approval", False)),
            constraints=cfg.get("constraints") or {},
            provenance_required=cfg.get("provenance_required"),
            reason=cfg.get("reason"),
        )
    return result


def build_opa_input(
    tool_name: str,
    capability: str,
    taint: bool,
    side_effect_type: str,
    descriptor_hash_valid: bool,
    allowlist: Iterable[str],
    capability_map: Dict[str, bool],
    approval_required: Iterable[str] = (),
) -> Dict[str, Any]:
    """Assemble the OPA input object from Python domain types.

    This is the single authoritative mapping between the Python engine's
    argument surface and the Rego ``input`` document consumed by
    ``safe_mcp_proxy/policies/proxy.rego``.
    """
    return {
        "tool_name": tool_name,
        "capability": capability,
        "taint": taint,
        "side_effect_type": side_effect_type,
        "descriptor_hash_valid": descriptor_hash_valid,
        "allowlist": list(allowlist),
        "capability_map": dict(capability_map),
        "approval_required": list(approval_required),
    }


def compile_world_manifest(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    allowed_tools = raw.get("allowed_tools", [])
    capabilities = raw.get("capabilities", {})

    capability_map: Dict[str, bool] = {}
    approval_required: List[str] = []
    for capability, config in capabilities.items():
        if isinstance(config, dict):
            capability_map[capability] = bool(config.get("allowed", False))
            if bool(config.get("requires_approval", False)):
                approval_required.append(capability)
        else:
            capability_map[capability] = bool(config)

    taint_rules = raw.get("taint_rules", [])
    side_effects = raw.get("side_effects", {})
    capability_definitions = parse_capability_definitions(raw.get("capability_definitions", {}))

    skill_sources = parse_skill_sources(raw.get("skill_sources", {}))
    skill_capabilities = parse_skill_capabilities(capabilities, skill_sources)

    return {
        "world_id": raw.get("world_id", ""),
        "allowlist": allowed_tools,
        "capability_map": capability_map,
        "approval_required": approval_required,
        "taint_rules": taint_rules,
        "side_effect_policy": side_effects,
        "policy_engine": raw.get("policy_engine", "python"),
        "capability_definitions": capability_definitions,
        "skill_sources": skill_sources,
        "skill_capabilities": skill_capabilities,
    }
