# Forensic Replay: Deterministic Verification of Past Decisions

Re-evaluate past decisions against the current policy. `matches: false` means the world changed.

## How it works

```python
result = executor.replay({
    "tool": "send_email",
    "taint": True,
    "decision": "DENY",
    "rule": "tainted_external_side_effect",
})
# → {"matches": True, "replayed_decision": "DENY", ...}
```

Replay is deterministic: same inputs → same output. If the manifest changed since the original decision, `matches: False` with diverging `replayed_rule` vs `recorded_rule`.

## Configuration drift detection

| Scenario | Original | Replayed | Signal |
|----------|----------|----------|--------|
| Tool added to allowlist | ABSENT | ALLOW | policy relaxed |
| Capability disabled after review | ALLOW | ABSENT | policy tightened |
| Schema mutated | ALLOW | DENY/descriptor_drift | schema drifted |

## Bundle replay (offline)

```python
replayer = BundleReplayer(bundle_path)
mismatches = [r for r in replayer.replay_all() if not r["matches"]]
```

Export a bundle via `/export/bundle`, share with an auditor, replay offline — no live system access needed.

**See also:** [`wiki/audit-replay.md`](../../wiki/audit-replay.md) · [`bundle_replay.py`](../../safe_mcp_proxy/bundle_replay.py)
