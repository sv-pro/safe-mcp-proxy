# `execution_mode.py`

## Role

Defines the `ExecutionMode` enum, which controls how the executor handles an `ASK` decision. Set on the `Provenance` object at request time; propagated through `Provenance.derive()` to child tool calls.

## Values

| Value | Meaning |
|-------|---------|
| `INTERACTIVE` | Human interaction is available — ASK creates an approval token and pauses execution |
| `BACKGROUND` | No interaction possible — ASK falls back immediately to `DENY / ask_unavailable_in_background` |

## Effect on ASK

```
INTERACTIVE → approval_store.create(); return {decision: ASK, approval_token: <uuid>}
BACKGROUND  → return {decision: DENY, rule: ask_unavailable_in_background}
```

INTERACTIVE is the default when `ExecutionMode` is not specified.

## CLI usage

Set via `--mode` flag:

```bash
python -m safe_mcp_proxy.main --tool send_email --source cli \
  --payload '{"to":"x@example.com","body":"hi"}' \
  --mode interactive
```

## Used by

- [[src/safe_mcp_proxy/provenance]] — `Provenance.execution_mode` field (default: `INTERACTIVE`)
- [[src/safe_mcp_proxy/executor]] — checks `provenance.execution_mode` in the ASK branch
- [[src/safe_mcp_proxy/approval_store]] — stored in `PendingApproval.execution_mode`
- [[src/safe_mcp_proxy/main]] — parsed from `--mode` CLI argument

## See also

- [[ask-approval]] — full ASK decision lifecycle
- [[src/safe_mcp_proxy/approval_store]] — token store that handles INTERACTIVE ASK
- [[src/safe_mcp_proxy/executor]] — dispatches on execution mode for ASK
- [[src/safe_mcp_proxy/provenance]] — carries `execution_mode` through the pipeline
