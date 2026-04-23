from typing import Any, Dict, Iterable

import yaml


def build_opa_input(
    tool_name: str,
    capability: str,
    taint: bool,
    side_effect_type: str,
    descriptor_hash_valid: bool,
    allowlist: Iterable[str],
    capability_map: Dict[str, bool],
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
    }


def compile_world_manifest(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    allowed_tools = raw.get("allowed_tools", [])
    capabilities = raw.get("capabilities", {})
    capability_map = {
        capability: bool(config.get("allowed", False)) if isinstance(config, dict) else bool(config)
        for capability, config in capabilities.items()
    }

    taint_rules = raw.get("taint_rules", [])
    side_effects = raw.get("side_effects", {})

    return {
        "world_id": raw.get("world_id", ""),
        "allowlist": allowed_tools,
        "capability_map": capability_map,
        "taint_rules": taint_rules,
        "side_effect_policy": side_effects,
        "policy_engine": raw.get("policy_engine", "python"),
    }
