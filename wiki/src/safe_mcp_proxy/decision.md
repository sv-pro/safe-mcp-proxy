# `decision.py`

## Role

Defines the `Decision` enum — the complete set of valid policy outcomes.

## Key symbols

| Name | Kind | Description |
|------|------|-------------|
| `Decision` | str enum | Four values: `ALLOW`, `DENY`, `ABSENT`, `SIMULATE` |
| `Decision.parse` | classmethod | Safe parse: returns enum member or original string on unknown value |
| `Decision.values` | classmethod | Returns `("ALLOW", "DENY", "ABSENT", "SIMULATE")` |

## Values

| Value | Meaning |
|-------|---------|
| `ALLOW` | All checks passed; execute the tool |
| `DENY` | Tool visible but invocation blocked by policy |
| `ABSENT` | Tool does not exist in this world |
| `SIMULATE` | Reserved for future approve/simulate workflows |

`Decision` inherits from `str`, so `decision.value` equals `str(decision)` and JSON serialization works naturally.

## Used by

- [[src/safe_mcp_proxy/policy_engine]] — return type of `decide()`
- [[src/safe_mcp_proxy/executor]] — branching on `policy.decision`
- [[src/safe_mcp_proxy/trace_store]] — `TraceRecord.decision` field
- [[src/api/index]] — `Decision` values in stats counter

## See also

- [[absent-deny]] — ABSENT and DENY semantics
