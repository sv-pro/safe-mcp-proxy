# `api/`

## Role

FastAPI HTTP layer. Exposes the enforcement pipeline, trace store, scenario runner, world compare, and bundle export over HTTP.

## Key symbols

| Name | Kind | Description |
|------|------|-------------|
| `create_app` | function | Factory that builds and returns the FastAPI app |
| `app` | module-level | Default app instance (`create_app()`) |

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Serves `ui/index.html` |
| `GET` | `/traces` | Last N trace records from `TraceStore` |
| `GET` | `/traces/{trace_id}` | Single trace by line ID |
| `POST` | `/replay/{trace_id}` | Re-evaluate policy for a recorded trace |
| `POST` | `/scenarios/{name}/run` | Execute a named scenario |
| `POST` | `/compare` | Run one scenario across multiple worlds |
| `GET` | `/export/bundle` | Export manifest + trace as a shareable bundle |
| `GET` | `/stats` | Decision counts (ALLOW/DENY/ABSENT/SIMULATE) |

## Startup behavior

`create_app()`:
1. Calls `_seed_if_empty()` — copies `seeds/demo.jsonl` to `audit.jsonl` if the log is empty
2. Builds `TraceStore` from `audit.jsonl`
3. Builds `Executor` via `build_executor(base_dir)`
4. Adds CORS middleware (`allow_origins=["*"]`)

## `/compare` request body

```json
{"scenario": "benign_flow", "worlds": ["world_a", "world_b"]}
```

Returns per-world `{decision, rule}` for the same scenario.

## Depends on

- [[src/safe_mcp_proxy/main]] — `build_executor()`
- [[src/safe_mcp_proxy/trace_store]] — `TraceStore`
- [[src/safe_mcp_proxy/scenarios/index]] — `scenarios.run()`, `scenarios.get()`
- [[src/safe_mcp_proxy/compiler]] — `compile_world_manifest()` for bundle export
- [[src/safe_mcp_proxy/provenance]] — `Provenance.from_source()`
- [[src/safe_mcp_proxy/decision]] — `Decision` for stats counter

## See also

- [[audit-replay]] — trace and replay semantics
- [[architecture]] — full pipeline this API exposes
