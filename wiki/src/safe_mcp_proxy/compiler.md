# `compiler.py`

## Role

Parses a world manifest YAML file into a typed runtime config dict. Also provides the OPA input assembler.

## Key symbols

| Name | Kind | Description |
|------|------|-------------|
| `compile_world_manifest` | function | Parses YAML manifest → typed dict |
| `build_opa_input` | function | Assembles the `input` object for OPA evaluation |

## `compile_world_manifest()` output

```python
{
    "world_id":              str,                    # from world_id
    "allowlist":             list[str],              # from allowed_tools
    "capability_map":        dict[str, bool],        # from capabilities[*].allowed
    "approval_required":     list[str],              # from capabilities[*].requires_approval
    "taint_rules":           list,                   # from taint_rules
    "side_effect_policy":    dict,                   # from side_effects
    "policy_engine":         str,                    # from policy_engine (default "python")
    "capability_definitions": dict[str, CapabilityDef],  # from capability_definitions section
}
```

`capability_map` handles both dict (`{allowed: true}`) and bare bool values in the YAML.

`capability_definitions` is parsed via `parse_capability_definitions()` from [[src/safe_mcp_proxy/capability_dsl]]. An empty dict is returned when the section is absent.

## `build_opa_input()` purpose

Single authoritative mapping from Python domain types to the OPA `input` document consumed by `proxy.rego`. Called by [[src/safe_mcp_proxy/opa_engine]] before each OPA evaluation.

## Depends on

- `yaml` (PyYAML)
- [[src/safe_mcp_proxy/capability_dsl]] — `parse_capability_definitions()`

## Used by

- [[src/safe_mcp_proxy/main]] — `compile_world_manifest()` in `build_executor()`
- [[src/safe_mcp_proxy/opa_engine]] — `build_opa_input()` before each OPA call
- [[src/api/index]] — `compile_world_manifest()` for bundle export

## See also

- [[world-manifest]] — the YAML format this function parses
- [[policy-engine]] — `allowlist` and `capability_map` output feeds directly into `PolicyEngine`
- [[absent-deny]] — `allowlist` produced here is what makes tools ABSENT when missing
- [[architecture]] — compiler runs at startup as part of `build_executor()` wiring
