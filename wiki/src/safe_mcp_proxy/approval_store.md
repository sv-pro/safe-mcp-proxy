# `approval_store.py`

## Role

In-memory store for pending approval tokens. Created when the executor emits an ASK decision in INTERACTIVE mode. Persists the original request context so the tool can be re-executed after the human approves.

## Key symbols

| Name | Kind | Description |
|------|------|-------------|
| `PendingApproval` | dataclass | One approval record — token, tool context, status |
| `ApprovalStore` | class | Dict-backed store for `PendingApproval` objects |
| `ApprovalStore.create` | method | Generates UUID token, stores `PendingApproval`; returns token string |
| `ApprovalStore.get` | method | Returns `PendingApproval` by token or `None` |
| `ApprovalStore.approve` | method | Transitions `pending → approved`; returns `bool` |
| `ApprovalStore.reject` | method | Transitions `pending → rejected`; returns `bool` |
| `ApprovalStore.mark_executed` | method | Transitions `approved → executed`; returns `bool` |

## `PendingApproval` fields

| Field | Type | Description |
|-------|------|-------------|
| `token` | `str` | UUID — unique approval identifier |
| `tool_name` | `str` | Tool that was requested |
| `payload` | `dict` | Original tool arguments |
| `source_channel` | `str` | Provenance channel (`cli`, `web`, etc.) |
| `tainted` | `bool` | Whether the original request was tainted |
| `execution_mode` | `str` | `"INTERACTIVE"` or `"BACKGROUND"` (stored as str) |
| `created_at` | `str` | ISO-8601 UTC timestamp |
| `status` | `str` | `"pending"` \| `"approved"` \| `"rejected"` \| `"executed"` |

## Status state machine

```
pending
  ├─ approve()  → approved  → mark_executed()  → executed
  └─ reject()   → rejected
```

Transitions are guarded — `approve()` and `reject()` only succeed from `pending`; `mark_executed()` only succeeds from `approved`. All others return `False`.

## Used by

- [[src/safe_mcp_proxy/executor]] — `Executor.__init__` accepts an `ApprovalStore`; `execute()` calls `create()`; `execute_approved()` calls `mark_executed()`; `reject_approval()` calls `reject()`
- [[src/api/index]] — `app.state.executor.approval_store` is accessed directly for status queries

## See also

- [[ask-approval]] — full ASK decision lifecycle
- [[src/safe_mcp_proxy/execution_mode]] — `execution_mode` stored in each `PendingApproval`
- [[src/safe_mcp_proxy/executor]] — orchestrates the approval flow
- [[src/api/index]] — `/approvals/{token}` HTTP endpoints
