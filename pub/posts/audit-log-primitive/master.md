# The Audit Log as a Security Primitive

Most systems have an audit log. Few treat it as a security primitive.

The distinction: an event log tells you what happened. A forensic audit log tells you
what decision was made, which rule made it, what the state was at that moment, and whether
that decision would be reproducible today.

safe-mcp-proxy's audit log is the second kind.

---

## What is logged

Every `execute()` call appends a JSON line to `safe_mcp_proxy/logs/audit.jsonl`:

```json
{
  "timestamp": "2026-04-26T12:00:00+00:00",
  "tool": "send_email",
  "decision": "DENY",
  "rule": "tainted_external_side_effect",
  "taint": true,
  "descriptor_hash": "a3f8c21d...",
  "source_channel": "web"
}
```

Every field is a forensic anchor:

| Field | Forensic use |
|-------|-------------|
| `timestamp` | When exactly did this decision happen? |
| `tool` | What tool was targeted? |
| `decision` | What did the policy engine decide? |
| `rule` | Which specific rule fired? |
| `taint` | Was the request provenance tainted? |
| `descriptor_hash` | What was the tool schema at this moment? |
| `source_channel` | Where did the request originate? |

---

## Append-only by design

The file is opened with mode `"a"` on every write. There is no mechanism to update or
delete existing entries. This is not a missing feature — it is a deliberate property.

An audit log that can be modified is not an audit log. It is a history that someone
controls.

Append-only means: if an entry exists, it represents a real decision at that timestamp.
You cannot retroactively change what happened. Forensic investigations can trust the
log.

---

## The descriptor_hash field

The descriptor hash in each entry is the SHA256 of the tool schema at the time of the
decision. This enables two forensic operations:

1. **Schema verification:** Compare the recorded hash against the hash of the current
   schema. If they differ, the schema changed between the original decision and now.

2. **Drift detection between entries:** If two entries for the same tool have different
   `descriptor_hash` values, the schema was mutated between those invocations. You can
   pinpoint exactly when.

---

## ASK entries: two-entry pattern

When a capability requires approval, an ASK invocation in INTERACTIVE mode produces
two entries:

```json
{"decision": "ASK", "rule": "approval_required", "tool": "send_email", ...}
{"decision": "ALLOW", "rule": "approved", "tool": "send_email", ...}
```

Or, if rejected:

```json
{"decision": "ASK", "rule": "approval_required", "tool": "send_email", ...}
{"decision": "DENY", "rule": "approval_rejected", "tool": "send_email", ...}
```

In BACKGROUND mode, there is one entry:

```json
{"decision": "DENY", "rule": "ask_unavailable_in_background", "tool": "send_email", ...}
```

The two-entry pattern is not a coincidence. It creates an auditable lifecycle: you can
see not just the final decision but the moment the approval gate was triggered and the
moment it was resolved.

---

## The TraceStore

`trace_store.py` wraps the audit JSONL as a typed, queryable interface:

```python
store = TraceStore(audit_log_path)
store.all()                       # all records
store.last(10)                    # 10 most recent
store.filter(
    decision="DENY",
    tool="send_email",
    since="2026-04-26T00:00:00Z"
)                                 # filtered records
```

The API exposes `/traces` and `/traces/{id}` built on TraceStore. Queries run over the
raw JSONL without a database layer.

---

## What the audit log is not

The audit log is not:
- **Metrics:** It is not aggregated or summarized at write time. Aggregation happens at
  read time via TraceStore queries.
- **Application logging:** It does not record errors, stack traces, or debug output.
  Every entry is a policy decision and nothing else.
- **Mutable state:** It cannot be used as a queue, a checkpoint, or a recoverable state
  store. It is strictly read from the beginning and appended to at the end.

These constraints are the properties that make it forensically useful.

---

## See also

- [Repository](https://github.com/sv-pro/safe-mcp-proxy)
- `safe_mcp_proxy/executor.py` — `_audit()` implementation
- `safe_mcp_proxy/trace_store.py` — queryable interface
- `wiki/audit-replay.md` — concept page including replay
- The next post: forensic-replay — re-running past decisions against current policy
