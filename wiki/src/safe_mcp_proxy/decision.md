# `decision.py`

## Role

Defines the `Decision` enum — the complete set of valid policy outcomes.

## Key symbols

| Name | Kind | Description |
|------|------|-------------|
| `Decision` | str enum | Five values: `ALLOW`, `DENY`, `ABSENT`, `SIMULATE`, `ASK` |
| `Decision.parse` | classmethod | Safe parse: returns enum member or original string on unknown value |
| `Decision.values` | classmethod | Returns `("ALLOW", "DENY", "ABSENT", "SIMULATE", "ASK")` |

## Values

| Value | Meaning |
|-------|---------|
| `ALLOW` | All checks passed; execute the tool |
| `DENY` | Tool visible but invocation blocked by policy (terminal) |
| `ABSENT` | Tool does not exist in this world |
| `SIMULATE` | Return mock result without real execution (no side effects) |
| `ASK` | Invocation structurally valid but capability requires approval; execution paused |

`Decision` inherits from `str`, so `decision.value` equals `str(decision)` and JSON serialization works naturally.

## Used by

- [[src/safe_mcp_proxy/policy_engine]] — return type of `decide()`
- [[src/safe_mcp_proxy/executor]] — branching on `policy.decision`
- [[src/safe_mcp_proxy/trace_store]] — `TraceRecord.decision` field
- [[src/api/index]] — `Decision` values in stats counter

## See also

- [[absent-deny]] — ABSENT and DENY semantics
- [[ask-approval]] — ASK decision: approval lifecycle, execution modes, API endpoints
- [[policy-engine]] — `decide()` returns a `PolicyResult` carrying a `Decision`
- [[audit-replay]] — `decision` field is logged in every audit entry
- [[architecture]] — `Decision` enum is the return type flowing through stage 3→4 of the pipeline
