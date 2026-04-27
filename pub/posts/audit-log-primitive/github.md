# The Audit Log as a Security Primitive

An event log tells you what happened. safe-mcp-proxy's audit log tells you what decision was made, which rule made it, and whether that decision is reproducible today.

## What's logged

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

`descriptor_hash` pins the tool schema at decision time — you can verify later whether the schema changed between two entries or between an entry and today.

## Append-only by design

Mode `"a"` on every write. No update or delete mechanism. An audit log that can be modified is not an audit log.

## ASK: two-entry lifecycle

```json
{"decision": "ASK", "rule": "approval_required", ...}
{"decision": "ALLOW", "rule": "approved", ...}   // or DENY / approval_rejected
```

## Query via TraceStore

```python
store = TraceStore(audit_log_path)
store.filter(decision="DENY", tool="send_email", since="2026-04-26T00:00:00Z")
```

**See also:** [`wiki/audit-replay.md`](../../wiki/audit-replay.md) · [`trace_store.py`](../../safe_mcp_proxy/trace_store.py)
