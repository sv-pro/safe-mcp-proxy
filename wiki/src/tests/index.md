# `tests/`

## Role

Test suite for the proxy pipeline, API layer, OPA engine, trace store, scenarios, Atlassian integration, Gemini adapter, and skill subsystem.

## Files

| File | Covers |
|------|--------|
| `test_proxy.py` | Core pipeline: `TestProxy` (single-world decisions) + `TestMultipleWorlds` (cross-world policy variation) |
| `test_api.py` | FastAPI endpoints via TestClient |
| `test_opa_engine.py` | `OPAPolicyEngine` subprocess and REST evaluators |
| `test_trace_store.py` | `TraceStore` filtering and streaming |
| `test_scenarios.py` | Named scenario registration and execution |
| `test_run_demo.py` | `run_demo.py` smoke test |
| `test_attack_corpus.py` | Attack corpus loader and scenario validation |
| `test_mcpzero.py` | MCPZero demo pipeline — baseline vs protected mode |
| `test_capability_projection.py` | `CapabilityProjectionEngine` filtering rules |
| `test_skill_registry.py` | `SkillSourceRegistry` import and catalogue |
| `test_skill_execution_guard.py` | Executor skill execution guard (7-step constraint check) |
| `test_skill_manifest.py` | Skill capability manifest parsing and validation |
| `test_skill_trace.py` | Skill execution audit trace fields |
| `test_gemini_adapter.py` | `GeminiAdapter.parse()` and `format_response()` |
| `test_atlassian_policy.py` | `ManifestPolicyEngine` five-rule decision logic |
| `test_atlassian_filter.py` | `CapabilityFilter` allowlist/denylist composition |
| `test_atlassian_flow.py` | `FlowContext` label tracking and data-flow rules |
| `test_atlassian_passthrough.py` | `MCPPassthrough` full pipeline (stub mode) |
| `test_atlassian_adapters.py` | `ATLASSIAN_TOOLS` registry + `apply_safe_abstraction` |
| `test_atlassian_demo.py` | Atlassian attack-and-block integration demo |
| `test_atlassian_observability.py` | `AtlassianTraceReader` filtering and stats |

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
- [[policy-engine]] — test cases cover all 6 decision paths
- [[world-manifest]] — `TestMultipleWorlds` tests cross-world policy variation
- [[provenance-taint]] — `test_tainted_external_is_denied` tests taint rule directly
- [[descriptor-drift]] — `test_descriptor_drift_is_denied` tests schema mutation detection
- [[architecture]] — tests exercise the full executor pipeline end-to-end
