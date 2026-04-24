# Audit Log & Replay

Every policy decision is recorded in an append-only JSONL log. The log supports forensic replay: re-running a recorded decision deterministically and verifying it matches.

## Audit log

**Location**: `safe_mcp_proxy/logs/audit.jsonl`

**Format**: one JSON object per line, written by `executor._audit()` after every `execute()` call.

Each entry has these fields:

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | ISO-8601 UTC | When the decision was made |
| `tool` | `str` | Tool name |
| `decision` | `str` | `ALLOW`, `DENY`, `ABSENT`, `ASK`, or `SIMULATE` |
| `rule` | `str` | Policy rule that was hit |
| `taint` | `bool` | Whether the request was tainted |
| `descriptor_hash` | `str` | SHA256 of the tool schema at call time |
| `source_channel` | `str` | `cli`, `email`, `web`, or `tool_output` |

The file is strictly append-only. `_audit()` opens with mode `"a"` and never reads or modifies existing entries.

### ASK audit entries

An ASK invocation in INTERACTIVE mode produces **two** audit entries:

1. When the approval token is issued: `decision: ASK, rule: approval_required`
2. After the human decides:
   - Approved: `decision: ALLOW, rule: approved`
   - Rejected: `decision: DENY, rule: approval_rejected`

An ASK invocation in BACKGROUND mode produces a **single** entry: `decision: DENY, rule: ask_unavailable_in_background`. The decision is recorded as DENY because no interaction is possible and nothing executes.

## Replay

`executor.replay(audit_entry)` re-evaluates the [[policy-engine]] for a recorded entry and checks whether the new decision matches the recorded one.

```python
result = executor.replay({
    "tool": "send_email",
    "taint": True,
    "decision": "DENY",
    "rule": "tainted_external_side_effect",
})
# → {"recorded_decision": "DENY", "replayed_decision": "DENY", "matches": True, ...}
```

Replay is deterministic: same allowlist + capability_map + taint + tool → same decision. If the manifest or tool registry changed since the original decision, `matches` will be `False`, indicating configuration drift.

## TraceStore

[[src/safe_mcp_proxy/trace_store]] wraps the audit JSONL as a typed, queryable store. Key methods:
- `all()` — all records
- `last(n)` — most recent n records
- `filter(decision=, tool=, since=, until=)` — filtered records

The API layer uses `TraceStore` to serve `/traces` and `/traces/{id}` endpoints.

## Bundle replay

[[src/safe_mcp_proxy/bundle_replay]] enables offline replay from a saved bundle (manifest + traces). Used with the `/export/bundle` API endpoint.

## See also

- [[ask-approval]] — ASK decision lifecycle and its two-entry audit pattern
- [[src/safe_mcp_proxy/executor]] — `_audit()` and `replay()` implementation
- [[src/safe_mcp_proxy/trace_store]] — typed read interface over the log
- [[src/safe_mcp_proxy/bundle_replay]] — offline bundle replay
- [[src/api/index]] — HTTP endpoints for traces and replay
