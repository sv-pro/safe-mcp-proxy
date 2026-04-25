# Architecture

The executor runs every tool invocation through a fixed 5-stage pipeline. Each stage is deterministic and has a single responsibility.

## Pipeline

```
Request (tool name + payload + source channel + execution mode)
  ↓
Provenance  — classify source channel; set taint flag; carry execution_mode
  ↓
Registry    — look up tool; filter against world allowlist → ABSENT if missing
  ↓
PolicyEngine — evaluate 6 decision paths (see below)
  ↓
Executor    — dispatch to handler or simulate_external(); write to audit.jsonl
  ↓
Response    { decision, rule, result }
```

Every stage feeds into the next. The pipeline is synchronous and has no side effects until the ALLOW path in the Executor stage.

## Stage breakdown

### 1. Provenance
`Provenance.from_source(source_channel, execution_mode)` classifies the request origin. Taint is set immediately if the channel is `email`, `web`, or `tool_output`. `execution_mode` (default: `INTERACTIVE`) is also set here and flows unchanged through the pipeline; it is never mutated. See [[src/safe_mcp_proxy/execution_mode]].

### 2. Registry lookup
`executor._tool_context(tool_name)` calls `registry.get_tool(tool_name)`. If the tool is not in the allowlist, `None` is returned. The side-effect type defaults to `"unknown"` and the hash check is skipped (hash_ok=True) — absence is handled by the PolicyEngine, not here.

The registry also holds scoped tools built from `capability_definitions` in the manifest. These synthetic tools expose only `actor_input` args in their schema and inject `literal` args automatically. They are indistinguishable from raw tools at the executor level — the same lookup, the same dispatch path.

### 3. PolicyEngine decision
`policy_engine.decide(...)` evaluates 6 rules in order and returns `PolicyResult(decision, rule_hit)`. See [[policy-engine]] for the full rule set.

### 4. Executor dispatch
Four execution paths based on `policy.decision`:
- **ALLOW** — if `simulate_external=True` and tool has `side_effect_type == "external"`: call `simulate_external_action()`. Otherwise: call `registry.execute_tool(tool_name, payload)`.
- **DENY** — return `{"error": "Denied by policy", "reason": rule_hit}`. No execution.
- **ASK / INTERACTIVE** — call `approval_store.create()` to generate a UUID token; return `{"decision": "ASK", "approval_token": "<uuid>", "result": null}`. Execution pauses pending human decision.
- **ASK / BACKGROUND** — interaction unavailable; fall back immediately to DENY with rule `"ask_unavailable_in_background"`. No execution.
- **ABSENT** — return `{"error": "Action does not exist in this world"}`. No execution.

### 5. Audit write
`_audit()` appends a JSON line to `audit.jsonl` regardless of decision outcome. Every invocation is logged. ASK in BACKGROUND mode is logged as DENY.

## Component map

| Component | Module | Role |
|-----------|--------|------|
| `Executor` | [[src/safe_mcp_proxy/executor]] | Orchestrates all stages |
| `ToolRegistry` | [[src/safe_mcp_proxy/registry]] | Tool definitions and allowlist filtering |
| `PolicyEngine` | [[src/safe_mcp_proxy/policy_engine]] | Pure decision logic |
| `OPAPolicyEngine` | [[src/safe_mcp_proxy/opa_engine]] | OPA/Rego drop-in for PolicyEngine |
| `Provenance` | [[src/safe_mcp_proxy/provenance]] | Source channel, taint, and execution mode |
| `ExecutionMode` | [[src/safe_mcp_proxy/execution_mode]] | INTERACTIVE vs BACKGROUND — controls ASK behavior |
| `ApprovalStore` | [[src/safe_mcp_proxy/approval_store]] | In-memory token store for pending approvals |
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
6. Returns fully configured `Executor` (with a fresh `ApprovalStore`)

The compiled manifest is immutable once `build_executor()` returns.

## See also

- [[world-manifest]] — the static world definition
- [[policy-engine]] — the 6 decision paths
- [[absent-deny]] — the two terminal failure modes
- [[ask-approval]] — the ASK provisional gate and approval lifecycle
- [[provenance-taint]] — taint propagation
- [[audit-replay]] — the audit trail
- [[src/safe_mcp_proxy/execution_mode]] — INTERACTIVE vs BACKGROUND
