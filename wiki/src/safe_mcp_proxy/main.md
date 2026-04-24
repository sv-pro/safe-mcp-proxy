# `main.py`

## Role

CLI entrypoint and `build_executor()` assembly function. Wires all components together from a world manifest.

## Key symbols

| Name | Kind | Description |
|------|------|-------------|
| `build_executor` | function | Assembles a fully configured `Executor` from `base_dir` + optional `world_id` + optional `engine` |
| `main` | function | CLI arg parsing and single-invocation execution |
| `_resolve_manifest_path` | function | Locates the correct YAML file for a given `world_id` |
| `_build_policy_engine` | function | Instantiates `PolicyEngine` or `OPAPolicyEngine` based on `engine` string |
| `_load_simulation_flag` | function | Reads `simulation.external_side_effects` from `config/policy.yaml` |

## `build_executor()` steps

```
1. _resolve_manifest_path(base_dir, world_id)
2. compile_world_manifest(manifest_path)
3. ToolRegistry.with_mock_tools(allowlist)
4. _build_policy_engine(manifest_tables, resolved_engine, base_dir)
5. _load_simulation_flag(config/policy.yaml)
6. return Executor(registry, policy_engine, audit_log_path, simulate_external)
```

## Manifest resolution order

```
world_id=None  → base_dir/world_manifest.yaml
world_id="x"  → base_dir/safe_mcp_proxy/config/worlds/x.yaml   (preferred)
              → base_dir/worlds/x.yaml                          (fallback)
              → FileNotFoundError if neither exists
```

## CLI flags

```
--tool      required  Tool name
--source    default="cli"   cli | email | web | tool_output
--payload   default="{}"    JSON payload string
--world     optional  World ID
--engine    optional  python | opa (overrides manifest's policy_engine key)
```

## Depends on

- [[src/safe_mcp_proxy/compiler]]
- [[src/safe_mcp_proxy/executor]]
- [[src/safe_mcp_proxy/policy_engine]]
- [[src/safe_mcp_proxy/opa_engine]]
- [[src/safe_mcp_proxy/provenance]]
- [[src/safe_mcp_proxy/registry]]

## Used by

- [[src/api/index]] — `build_executor()` to construct the app's executor
- [[src/safe_mcp_proxy/scenarios/index]] — `build_executor()` when no executor is passed

## See also

- [[architecture]] — how `build_executor()` fits the startup sequence
- [[world-manifest]] — manifest resolution and format
- [[provenance-taint]] — `Provenance.from_source(args.source)` is created here
- [[absent-deny]] — CLI prints decision which may be ABSENT or DENY
- [[policy-engine]] — `_build_policy_engine()` selects Python or OPA engine
- [[audit-replay]] — audit log path is wired here (`safe_mcp_proxy/logs/audit.jsonl`)
