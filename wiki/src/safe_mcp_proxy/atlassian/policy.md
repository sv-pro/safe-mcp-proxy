# `atlassian/policy.py`

## Role

`ManifestPolicyEngine` — deterministic five-rule decision engine for the Atlassian MCP path. Separate from the core `PolicyEngine`; operates on `allowed_tools`, `external_write_tools`, `arg_rules`, and `data_flow_rules` from a manifest YAML.

## Key symbols

| Name | Kind | Description |
|------|------|-------------|
| `PolicyDecision` | frozen dataclass | `(decision: str, rule: str, tool: str, tainted: bool)` |
| `ManifestPolicyEngine` | class | Stateful engine loaded from a manifest dict or YAML file |
| `ManifestPolicyEngine.__init__` | method | Parses allowlist, external_write, arg_rules, flow config |
| `ManifestPolicyEngine.evaluate` | method | Evaluates five rules; returns `PolicyDecision` |
| `ManifestPolicyEngine.from_yaml` | classmethod | Convenience constructor: reads YAML file → `cls(manifest)` |

## `evaluate()` rule order

```
1. tool_name not in allowlist (if allowlist non-empty)
   → ABSENT / tool_not_allowlisted

2. tainted source + tool in external_write_tools
   → DENY / tainted_source_blocks_external_write

3. FlowContext has data-flow label that denies this tool
   → DENY / <data_flow_rule_name>

4. Argument rule violated (arg value not in allowed_values)
   → DENY / <rule_name from manifest>

5. Default
   → ALLOW / default_allow
```

Note: if `allowed_tools` is empty in the manifest, rule 1 is skipped (passthrough mode — all tools visible).

## `evaluate()` signature

```python
def evaluate(
    self,
    tool_name: str,
    arguments: Dict[str, Any],
    tainted: bool,
    flow_context: Optional[FlowContext] = None,
) -> PolicyDecision
```

## Manifest keys consumed

| Key | Type | Meaning |
|-----|------|---------|
| `allowed_tools` | list[str] | Allowlist; empty = passthrough |
| `external_write_tools` | list[str] | Tools blocked when source is tainted |
| `arg_rules` | dict[tool → list[rule]] | Per-argument allowed_values constraints |
| `flow_rules.tainted_source_blocks_external_write` | bool | Global enable/disable for rule 2 (default: true) |
| `data_flow_rules` | list[DataFlowRule dicts] | Provenance-lite label constraints |

## Depends on

- [[src/safe_mcp_proxy/atlassian/flow]] — `DataFlowRule`, `parse_data_flow_rules`, `FlowContext`

## Used by

- [[src/safe_mcp_proxy/atlassian/passthrough]] — instantiated and consulted on every `tools/call`
- `api/main.py` — passes manifest path when building `MCPPassthrough`

## See also

- [[absent-deny]] — ABSENT and DENY semantics
- [[provenance-taint]] — taint concept mirrors core pipeline rule 4
- [[src/safe_mcp_proxy/atlassian/index]] — subpackage overview
