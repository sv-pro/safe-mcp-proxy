# Architecture

The executor runs every tool invocation through a fixed 5-stage pipeline. Each stage is deterministic and has a single responsibility.

## Pipeline

```
Request (tool name + payload + source channel)
  ↓
Provenance  — classify source channel; set taint flag
  ↓
Registry    — look up tool; filter against world allowlist → ABSENT if missing
  ↓
PolicyEngine — evaluate 5 decision paths (see below)
  ↓
Executor    — dispatch to handler or simulate_external(); write to audit.jsonl
  ↓
Response    { decision, rule, result }
```

Every stage feeds into the next. The pipeline is synchronous and has no side effects until the ALLOW path in the Executor stage.

## Stage breakdown

### 1. Provenance
`Provenance.from_source(source_channel)` classifies the request origin. Taint is set immediately if the channel is `email`, `web`, or `tool_output`. The provenance object flows unchanged through the pipeline; it is never mutated.

### 2. Registry lookup
`executor._tool_context(tool_name)` calls `registry.get_tool(tool_name)`. If the tool is not in the allowlist, `None` is returned. The side-effect type defaults to `"unknown"` and the hash check is skipped (hash_ok=True) — absence is handled by the PolicyEngine, not here.

### 3. PolicyEngine decision
`policy_engine.decide(...)` evaluates 5 rules in order and returns `PolicyResult(decision, rule_hit)`. See [[policy-engine]] for the full rule set.

### 4. Executor dispatch
Three execution paths based on `policy.decision`:
- **ALLOW** — if `simulate_external=True` and tool has `side_effect_type == "external"`: call `simulate_external_action()`. Otherwise: call `registry.execute_tool(tool_name, payload)`.
- **DENY** — return `{"error": "Denied by policy", "reason": rule_hit}`. No execution.
- **ABSENT** — return `{"error": "Action does not exist in this world"}`. No execution.

### 5. Audit write
`_audit()` appends a JSON line to `audit.jsonl` regardless of decision outcome. Every invocation is logged.

## Component map

| Component | Module | Role |
|-----------|--------|------|
| `Executor` | [[src/safe_mcp_proxy/executor]] | Orchestrates all stages |
| `ToolRegistry` | [[src/safe_mcp_proxy/registry]] | Tool definitions and allowlist filtering |
| `PolicyEngine` | [[src/safe_mcp_proxy/policy_engine]] | Pure decision logic |
| `OPAPolicyEngine` | [[src/safe_mcp_proxy/opa_engine]] | OPA/Rego drop-in for PolicyEngine |
| `Provenance` | [[src/safe_mcp_proxy/provenance]] | Source channel and taint |
| `descriptor` | [[src/safe_mcp_proxy/descriptor]] | SHA256 schema hashing |
| `compiler` | [[src/safe_mcp_proxy/compiler]] | YAML manifest → runtime config |
| `simulate` | [[src/safe_mcp_proxy/simulate]] | Mock external action |
| `main` | [[src/safe_mcp_proxy/main]] | CLI + `build_executor()` wiring |
| `TraceStore` | [[src/safe_mcp_proxy/trace_store]] | Read interface over audit log |
| `FastAPI app` | [[src/api/index]] | HTTP API layer |

## Startup wiring

`build_executor(base_dir, world_id, engine)` in [[src/safe_mcp_proxy/main]]:
1. Resolves manifest path (`world_manifest.yaml` or named world YAML)
2. Compiles manifest via `compile_world_manifest()` → typed tables
3. Creates `ToolRegistry.with_mock_tools(allowlist)`
4. Selects policy engine (`python` or `opa`)
5. Loads simulation flag from `config/policy.yaml`
6. Returns fully configured `Executor`

The compiled manifest is immutable once `build_executor()` returns.

## See also

- [[world-manifest]] — the static world definition
- [[policy-engine]] — the 5 decision paths
- [[absent-deny]] — the two failure modes
- [[provenance-taint]] — taint propagation
- [[audit-replay]] — the audit trail
