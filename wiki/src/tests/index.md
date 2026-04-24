# `tests/`

## Role

Test suite for the proxy pipeline, API layer, OPA engine, trace store, and scenarios.

## Files

| File | Covers |
|------|--------|
| `test_proxy.py` | Core pipeline: `TestProxy` (single-world decisions) + `TestMultipleWorlds` (cross-world policy variation) |
| `test_api.py` | FastAPI endpoints via TestClient |
| `test_opa_engine.py` | `OPAPolicyEngine` subprocess and REST evaluators |
| `test_trace_store.py` | `TraceStore` filtering and streaming |
| `test_scenarios.py` | Named scenario registration and execution |
| `test_run_demo.py` | `run_demo.py` smoke test |

## Running tests

```bash
# All tests
python -m unittest tests.test_proxy

# Single test
python -m unittest tests.test_proxy.TestProxy.test_benign_cli_read_allows
```

## `test_proxy.py` patterns

`TestProxy` setup:
- Creates `ToolRegistry.with_mock_tools(["read_file", "list_repo", "send_email"])`
- Creates `PolicyEngine` with allowlist and capability_map
- Creates a temp audit file (`safe_mcp_proxy_test_audit.jsonl`)
- Creates `Executor(registry, policy, audit_path, simulate_external=True)`

Key test cases:
- `test_benign_cli_read_allows` — CLI source → `ALLOW`
- `test_tainted_external_is_denied` — web source + send_email → `DENY`
- `test_descriptor_drift_is_denied` — mutated schema → `DENY`
- `test_non_allowlisted_tool_is_absent` — unknown tool → `ABSENT`
- `test_replay_*` — audit entry replay verification

`TestMultipleWorlds`:
- Writes temp world YAML files
- Verifies same input yields different decisions across `world_a` / `world_b`

## See also

- [[audit-replay]] — replay test patterns
- [[absent-deny]] — the outcomes being tested
