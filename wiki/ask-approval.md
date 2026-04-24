# ASK Decision & Approval Workflow

`ASK` is the third policy outcome. The tool is visible in the agent's world and the invocation is structurally valid, but the capability is gated by explicit human approval. Execution is paused until a human approves or rejects the pending token.

## How it differs from DENY and ABSENT

| Outcome | Meaning | Terminal? |
|---------|---------|-----------|
| `ABSENT` | Tool does not exist in this world | Yes — no action taken |
| `DENY` | Invocation blocked by policy | Yes — no action taken |
| `ASK` | Invocation paused, awaiting human decision | No — resolves to ALLOW or DENY |

DENY is final. ASK is provisional.

## Trigger

A capability marked `requires_approval: true` in the world manifest:

```yaml
capabilities:
  send_email:
    allowed: true
    requires_approval: true
```

The compiler adds `send_email` to the `approval_required` set. The PolicyEngine evaluates rule 5: if the tool's capability is in `approval_required`, the decision is `ASK / approval_required`.

Rule 5 is evaluated **after** all DENY rules. Tainted external requests are denied before reaching the approval check — taint takes priority over approval.

## Execution modes

The behavior of ASK depends on `ExecutionMode` in the `Provenance` object:

**INTERACTIVE** (default):
- `approval_store.create()` generates a UUID token
- Response: `{"decision": "ASK", "rule": "approval_required", "approval_token": "<uuid>", "result": null}`
- An audit entry is written: `decision: ASK, rule: approval_required`
- Execution pauses; the human receives the token and decides

**BACKGROUND**:
- Interaction is not possible — ASK falls back to DENY immediately
- Response: `{"decision": "DENY", "rule": "ask_unavailable_in_background", ...}`
- A single audit entry is written: `decision: DENY, rule: ask_unavailable_in_background`

## Approval lifecycle

```
pending
  ├─ approve(token)  → approved  → execute_approved(token)  → executed  (ALLOW / approved)
  └─ reject(token)   → rejected                                          (DENY / approval_rejected)
```

Tokens are stored in `ApprovalStore` (in-memory). Each token carries the original `tool_name`, `payload`, `source_channel`, `tainted`, and `execution_mode`.

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/approvals/{token}` | Get token status (`pending`, `approved`, `rejected`, `executed`) |
| `POST` | `/approvals/{token}/approve` | Approve token; triggers `execute_approved()` |
| `POST` | `/approvals/{token}/reject` | Reject token; logs as DENY / `approval_rejected` |

## Audit entries

An INTERACTIVE ASK flow produces **two** audit entries:

```jsonl
{"decision": "ASK", "rule": "approval_required", "tool": "send_email", ...}
{"decision": "ALLOW", "rule": "approved", "tool": "send_email", ...}
```

Or if rejected:
```jsonl
{"decision": "ASK", "rule": "approval_required", "tool": "send_email", ...}
{"decision": "DENY", "rule": "approval_rejected", "tool": "send_email", ...}
```

A BACKGROUND ASK produces a **single** entry:
```jsonl
{"decision": "DENY", "rule": "ask_unavailable_in_background", "tool": "send_email", ...}
```

## Replay semantics

Replay (`executor.replay()`) re-evaluates the policy engine against the recorded audit entry. An `ASK` entry replays as `ASK` if the manifest still has `requires_approval: true` for that capability — `matches: true`. If the manifest was changed to remove the approval requirement, the replayed decision is `ALLOW` — `matches: false`, indicating configuration drift.

## See also

- [[policy-engine]] — rule 5: `approval_required → ASK`
- [[absent-deny]] — ABSENT and DENY: the two terminal failure modes
- [[world-manifest]] — `requires_approval: true` capability config
- [[audit-replay]] — two-entry audit pattern for ASK
- [[src/safe_mcp_proxy/approval_store]] — token store implementation
- [[src/safe_mcp_proxy/execution_mode]] — INTERACTIVE vs BACKGROUND
- [[src/safe_mcp_proxy/executor]] — dispatch logic, `execute_approved()`, `reject_approval()`
- [[src/api/index]] — `/approvals/` HTTP endpoints
