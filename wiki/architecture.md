# Architecture

Every tool invocation passes through three conceptual layers and five implementation stages. Each layer answers a distinct question; each stage is deterministic and has a single responsibility.

## Three-layer model

```
Layer 1 — Ontology          Does this action exist in this world?
                              → ABSENT (stop) or PRESENT (continue)

Layer 2 — Policy            Is this action permitted in context?
                              → ALLOW / DENY / ASK

Layer 3 — Effect             In what reality does this action execute?
Virtualization                → EXECUTE / SIMULATE / PROXY / SANITIZE / TRUNCATE / DEFER
```

Policy is only reached for PRESENT actions. Effect Virtualization is only reached for ALLOW (or ASK-resolved-to-ALLOW) decisions. See [[effect-virtualization]] for the full effect mode taxonomy.

## Pipeline

```
Request (tool name + payload + source channel + execution mode)
  ↓
Provenance        — classify source channel; set taint flag; carry execution_mode
  ↓
Registry          — look up tool; filter against world allowlist
  ↓  [Layer 1: Ontology]
  ├─ ABSENT → return immediately; audit
  └─ PRESENT → continue
  ↓
PolicyEngine      — evaluate 6 decision paths in order
  ↓  [Layer 2: Policy]
  ├─ DENY   → return immediately; audit
  ├─ ASK    → create approval token (INTERACTIVE) or collapse to DENY (BACKGROUND); audit
  └─ ALLOW  → continue
  ↓
Executor dispatch — apply effect_mode; call handler or simulate_external()
  ↓  [Layer 3: Effect]
  ├─ EXECUTE   → registry.execute_tool() or upstream.call_tool()
  ├─ SIMULATE  → simulate_external_action() — synthetic result, no side effect
  └─ TRUNCATE  → (Atlassian) result filtered before return
  ↓
Audit             — append to audit.jsonl regardless of outcome
  ↓
Response          { decision, rule, result }
```

Every stage feeds into the next. The pipeline is synchronous. No side effects occur until the EXECUTE path in the Executor stage.

## Stage breakdown

### 1. Provenance
`Provenance.from_source(source_channel, execution_mode)` classifies the request origin. Taint is set immediately if the channel is `email`, `web`, or `tool_output`. `execution_mode` (default: `INTERACTIVE`) is set here and flows unchanged; it is never mutated. See [[src/safe_mcp_proxy/execution_mode]].

### 2. Registry lookup (Ontology — Layer 1)
`executor._tool_context(tool_name)` calls `registry.get_tool(tool_name)`. If the tool is not in the allowlist, `None` is returned. ABSENT is the Ontology Layer outcome — the action does not exist in this world.

The registry also holds scoped tools built from `capability_definitions`. These synthetic tools expose only `actor_input` args in their schema and inject `literal` args automatically. They are indistinguishable from raw tools at the executor level.

### 3. PolicyEngine decision (Policy — Layer 2)
`policy_engine.decide(...)` evaluates 6 rules in order and returns `PolicyResult(decision, rule_hit)`. Rules 1–2 produce ABSENT (ontological); rules 3–4 produce DENY (policy); rule 5 produces ASK; rule 6 is the default ALLOW. See [[policy-engine]].

### 4. Executor dispatch (Effect Virtualization — Layer 3)
For ALLOW decisions, the executor selects an effect mode:
- **EXECUTE** — `registry.execute_tool(tool_name, payload)` or upstream call (real side effect)
- **SIMULATE** — `simulate_external_action()` when `simulate_external=True` and `side_effect_type == "external"` (synthetic result, no real side effect)
- **TRUNCATE** / **SANITIZE** — applied by Atlassian passthrough via `arg_rules`

For non-ALLOW decisions:
- **DENY** — return error payload, no execution
- **ASK / INTERACTIVE** — `approval_store.create()` → UUID token; execution pauses
- **ASK / BACKGROUND** — immediate DENY with rule `"ask_unavailable_in_background"`
- **ABSENT** — return `{"error": "Action does not exist in this world"}`, no execution

### 5. Audit write
`_audit()` appends a JSON line to `audit.jsonl` regardless of decision. Every invocation is logged. ASK in BACKGROUND mode is logged as DENY.

## Component map

| Component | Module | Role |
|-----------|--------|------|
| `Executor` | [[src/safe_mcp_proxy/executor]] | Orchestrates all stages |
| `ToolRegistry` | [[src/safe_mcp_proxy/registry]] | Tool definitions and allowlist filtering (Layer 1) |
| `PolicyEngine` | [[src/safe_mcp_proxy/policy_engine]] | Pure decision logic (Layer 2) |
| `OPAPolicyEngine` | [[src/safe_mcp_proxy/opa_engine]] | OPA/Rego drop-in for PolicyEngine |
| `simulate` | [[src/safe_mcp_proxy/simulate]] | SIMULATE effect mode (Layer 3) |
| `Provenance` | [[src/safe_mcp_proxy/provenance]] | Source channel, taint, and execution mode |
| `ExecutionMode` | [[src/safe_mcp_proxy/execution_mode]] | INTERACTIVE vs BACKGROUND |
| `ApprovalStore` | [[src/safe_mcp_proxy/approval_store]] | In-memory token store for ASK lifecycle |
| `descriptor` | [[src/safe_mcp_proxy/descriptor]] | SHA256 schema hashing |
| `compiler` | [[src/safe_mcp_proxy/compiler]] | YAML manifest → runtime config |
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

- [[effect-virtualization]] — Layer 3 in depth: effect modes, security implications, current state
- [[absent-deny]] — Ontology (Layer 1) and Policy (Layer 2) decisions
- [[policy-engine]] — the 6 deterministic decision paths
- [[ask-approval]] — the ASK provisional gate and approval lifecycle
- [[provenance-taint]] — taint propagation
- [[audit-replay]] — the audit trail
- [[world-manifest]] — the static world definition
- [[src/safe_mcp_proxy/execution_mode]] — INTERACTIVE vs BACKGROUND
