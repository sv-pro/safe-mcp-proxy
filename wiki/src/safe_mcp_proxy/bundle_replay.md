# `bundle_replay.py`

## Role

Offline bundle replayer. Loads a saved demo bundle (manifest + traces) and replays each trace through the policy engine, reporting how many decisions match.

## Key symbols

| Name | Kind | Description |
|------|------|-------------|
| `replay_bundle` | function | Takes a bundle dict; returns `{total, matched, diverged, results}` |

## Bundle format

```json
{
  "manifest": {
    "allowlist": [...],
    "capability_map": {...}
  },
  "traces": [
    {
      "id": 1,
      "tool_requested": "read_file",
      "taint": false,
      "decision": "ALLOW",
      "rule_hit": "default_allow"
    }
  ]
}
```

Bundles are produced by the `/export/bundle` API endpoint (see [[src/api/index]]).

## `replay_bundle()` behavior

1. Reconstructs `ToolRegistry` and `PolicyEngine` from `bundle["manifest"]`
2. Creates an `Executor` with `audit_log_path=os.devnull` (no logging)
3. For each trace, calls `executor.replay(audit_entry)`
4. Returns summary: `{total, matched, diverged, results}`

## CLI usage

```bash
python -m safe_mcp_proxy.bundle_replay path/to/bundle.json
```

## Depends on

- [[src/safe_mcp_proxy/executor]]
- [[src/safe_mcp_proxy/policy_engine]]
- [[src/safe_mcp_proxy/registry]]

## See also

- [[audit-replay]] — replay semantics
- [[policy-engine]] — `PolicyEngine` is reconstructed from bundle manifest and re-evaluated
- [[absent-deny]] — replay verifies that ABSENT/DENY/ALLOW decisions are reproducible
- [[architecture]] — bundle_replay is an offline variant of the executor pipeline
- [[src/api/index]] — `/export/bundle` produces the input to this module
