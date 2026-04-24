# `executor.py`

## Role

Orchestrates the full tool invocation pipeline. Dispatches to tool handlers, manages approval tokens, writes to the audit log, and supports forensic replay.

## Key symbols

| Name | Kind | Description |
|------|------|-------------|
| `ABSENT_MESSAGE` | constant | `"Action does not exist in this world"` — canonical ABSENT response string |
| `Executor` | class | Main orchestrator |
| `Executor.__init__` | method | Takes `registry`, `policy_engine`, `audit_log_path`, `simulate_external`, `approval_store` |
| `Executor.execute` | method | Runs one tool invocation through the full pipeline; returns `{decision, rule, result}` |
| `Executor.execute_approved` | method | Executes a previously ASK'd tool after its approval token is approved |
| `Executor.reject_approval` | method | Records a rejection for a pending approval token; logs as DENY / `approval_rejected` |
| `Executor.replay` | method | Re-evaluates a recorded audit entry; returns `{recorded_*, replayed_*, matches}` |
| `Executor._tool_context` | method | Looks up tool; returns `(tool, capability, side_effect_type, hash_ok)` |
| `Executor._audit` | method | Appends one JSON line to `audit_log_path` |

## Execution paths in `execute()`

```
policy.decision == ALLOW   → simulate_external_action() or registry.execute_tool()
policy.decision == DENY    → {"error": "Denied by policy", "reason": rule_hit}
policy.decision == ABSENT  → {"error": ABSENT_MESSAGE}
policy.decision == ASK
  execution_mode == BACKGROUND  → DENY / ask_unavailable_in_background
  execution_mode == INTERACTIVE → approval_store.create(); return {decision: ASK, approval_token: <uuid>}
(always) → _audit(...); return {decision, rule, result}
```

## Approval flow

After `execute()` returns ASK:
1. Human receives the `approval_token`
2. Human calls `approval_store.approve(token)` (or via `POST /approvals/{token}/approve`)
3. `execute_approved(token)` re-runs the tool — logs as ALLOW / `approved`

If rejected:
- `reject_approval(token)` — logs as DENY / `approval_rejected`

## Depends on

- [[src/safe_mcp_proxy/registry]] — `get_tool()`, `execute_tool()`
- [[src/safe_mcp_proxy/policy_engine]] — `decide()`
- [[src/safe_mcp_proxy/descriptor]] — `compute_descriptor_hash()`, `descriptor_hash_valid()`
- [[src/safe_mcp_proxy/provenance]] — `Provenance` type (carries `execution_mode`)
- [[src/safe_mcp_proxy/simulate]] — `simulate_external_action()`
- [[src/safe_mcp_proxy/decision]] — `Decision` enum
- [[src/safe_mcp_proxy/approval_store]] — `ApprovalStore` for ASK token lifecycle
- [[src/safe_mcp_proxy/execution_mode]] — `ExecutionMode` controls INTERACTIVE vs BACKGROUND behavior

## Used by

- [[src/safe_mcp_proxy/main]] — `build_executor()` constructs and returns it
- [[src/api/index]] — `app.state.executor` for HTTP execution, approval, and replay
- [[src/safe_mcp_proxy/scenarios/index]] — `scenarios.run()` calls `executor.execute()`

## See also

- [[ask-approval]] — ASK decision lifecycle
- [[audit-replay]] — audit format and replay semantics
- [[absent-deny]] — the two terminal failure modes
- [[policy-engine]] — `decide()` is called on every `execute()` call
- [[provenance-taint]] — `provenance.tainted` drives DENY rule 4
- [[descriptor-drift]] — `descriptor_hash_valid()` drives DENY rule 3
- [[world-manifest]] — compiled manifest tables are passed in at construction
- [[architecture]] — executor is the central orchestrator of the pipeline
