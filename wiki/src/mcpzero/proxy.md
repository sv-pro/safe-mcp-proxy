# `mcpzero/proxy/proxy.py`

## Role

Enforcement layer for the MCPZero Demo. Wraps `safe_mcp_proxy.main.build_executor`
so every tool call goes through the full policy pipeline. Used by `ScenarioRunner`
in `protected` mode.

## Key symbols

| Name | Kind | Description |
|------|------|-------------|
| `SafeMCPProxy` | class | Thin wrapper around `Executor` for the mcpzero_demo world |
| `SafeMCPProxy.__init__` | method | Calls `build_executor(base_dir, world_id="mcpzero_demo")` |
| `SafeMCPProxy.call` | method | Single tool call: builds `Provenance`, runs executor, returns normalised dict |
| `SafeMCPProxy.run` | method | Runs all steps in an `AttackScenario`; applies `_apply_poison` for mcp_poison type |
| `SafeMCPProxy._apply_poison` | method | Mutates a tool's schema in the registry to simulate descriptor drift |
| `_REPO_ROOT` | `Path` | Two parents up from `proxy.py` → repo root |
| `_WORLD_ID` | str | `"mcpzero_demo"` — selects `worlds/mcpzero_demo.yaml` |

## Normalised result dict

```python
{
    "tool":     str,
    "payload":  dict,
    "decision": "ALLOW" | "DENY" | "ABSENT",
    "rule":     str | None,
    "result":   Any,
}
```

## mcp_poison handling

When `scenario.type == "mcp_poison"` and `scenario.poison_tool` is set,
`_apply_poison()` replaces the named tool's schema in the registry with the
`tampered_schema` from the scenario before executing steps. This triggers
`descriptor_drift` detection in the policy engine.

## Depends on

- [[src/safe_mcp_proxy/main]] — `build_executor()`
- [[src/safe_mcp_proxy/provenance]] — `Provenance.from_source()`
- [[src/attacks/loader]] — `AttackScenario`

## Used by

- [[src/mcpzero/index]] — `ScenarioRunner` in protected mode

## See also

- [[descriptor-drift]] — the mechanism triggered by mcp_poison scenarios
- [[provenance-taint]] — how source_channel maps to taint
- [[world-manifest]] — `worlds/mcpzero_demo.yaml`
