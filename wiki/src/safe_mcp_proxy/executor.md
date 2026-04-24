# `executor.py`

## Role

Orchestrates the full tool invocation pipeline. Dispatches to tool handlers, writes to the audit log, and supports forensic replay.

## Key symbols

| Name | Kind | Description |
|------|------|-------------|
| `ABSENT_MESSAGE` | constant | `"Action does not exist in this world"` — canonical ABSENT response string |
| `Executor` | class | Main orchestrator |
| `Executor.__init__` | method | Takes `registry`, `policy_engine`, `audit_log_path`, `simulate_external` |
| `Executor.execute` | method | Runs one tool invocation through the full pipeline; returns `{decision, rule, result}` |
| `Executor.replay` | method | Re-evaluates a recorded audit entry; returns `{recorded_*, replayed_*, matches}` |
| `Executor._tool_context` | method | Looks up tool; returns `(tool, capability, side_effect_type, hash_ok)` |
| `Executor._audit` | method | Appends one JSON line to `audit_log_path` |

## Execution paths in `execute()`

```
policy.decision == ALLOW  → simulate_external_action() or registry.execute_tool()
policy.decision == DENY   → {"error": "Denied by policy", "reason": rule_hit}
policy.decision == ABSENT → {"error": ABSENT_MESSAGE}
(always) → _audit(...); return {decision, rule, result}
```

## Depends on

- [[src/safe_mcp_proxy/registry]] — `get_tool()`, `execute_tool()`
- [[src/safe_mcp_proxy/policy_engine]] — `decide()`
- [[src/safe_mcp_proxy/descriptor]] — `compute_descriptor_hash()`, `descriptor_hash_valid()`
- [[src/safe_mcp_proxy/provenance]] — `Provenance` type
- [[src/safe_mcp_proxy/simulate]] — `simulate_external_action()`
- [[src/safe_mcp_proxy/decision]] — `Decision` enum

## Used by

- [[src/safe_mcp_proxy/main]] — `build_executor()` constructs and returns it
- [[src/api/index]] — `app.state.executor` for HTTP execution and replay
- [[src/safe_mcp_proxy/scenarios/index]] — `scenarios.run()` calls `executor.execute()`

## See also

- [[audit-replay]] — audit format and replay semantics
- [[absent-deny]] — the two failure modes
