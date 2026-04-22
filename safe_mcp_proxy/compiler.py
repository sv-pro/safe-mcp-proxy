from typing import Any, Dict

import yaml


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
    }
