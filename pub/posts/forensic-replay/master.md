# Forensic Replay: Deterministic Verification of Past Decisions

After an incident, the question is not just "what happened?" It is "would our current
policy have prevented this?"

These are different questions. The first requires an audit log. The second requires
deterministic replay — the ability to re-evaluate a past decision against the current
policy engine and compare outcomes.

---

## What replay is

`executor.replay(audit_entry)` takes a recorded audit entry and re-runs the policy
engine against it:

```python
result = executor.replay({
    "tool": "send_email",
    "taint": True,
    "source_channel": "web",
    "decision": "DENY",
    "rule": "tainted_external_side_effect",
})
```

The result:

```python
{
    "recorded_decision": "DENY",
    "recorded_rule": "tainted_external_side_effect",
    "replayed_decision": "DENY",
    "replayed_rule": "tainted_external_side_effect",
    "matches": True
}
```

If `matches: True`, the current policy would produce the same decision as the recorded one.
If `matches: False`, something changed — the world manifest was updated, the tool was
added or removed from the allowlist, or a capability flag was flipped.

---

## Why determinism enables replay

Replay works because the policy engine is deterministic. Given the same inputs, it
produces the same output. "Same inputs" means:

- Same tool name
- Same taint flag
- Same descriptor hash validity (computed from the current live schema)
- Same allowlist and capability map (from the current manifest)

If any of those differ between the original decision and the replay, `matches: False`
signals the discrepancy. The specific divergence is visible in the `replayed_rule` vs
`recorded_rule` fields.

---

## Configuration drift detection

`matches: False` is a configuration drift signal.

Scenarios where replay diverges:
- A tool was added to the allowlist after an incident (original: ABSENT, replayed: ALLOW)
- A capability was disabled after a policy review (original: ALLOW, replayed: ABSENT)
- The world manifest taint rules were updated (original: ALLOW, replayed: DENY)
- A tool's schema was mutated and never restored (original: ALLOW on valid hash, replayed: DENY on drifted hash)

For compliance purposes: replay across a time range of audit entries can detect when the
policy changed and what effect that change would have had on past decisions.

---

## Bundle replay

`bundle_replay.py` enables offline replay from a saved bundle — a snapshot of the
manifest plus a set of audit entries at a specific point in time.

The `/export/bundle` API endpoint creates a bundle. `BundleReplayer.replay_all()` runs
every entry in the bundle against the bundled manifest:

```python
replayer = BundleReplayer(bundle_path)
results = replayer.replay_all()
mismatches = [r for r in results if not r["matches"]]
```

This enables forensic investigations without access to the live system — share the bundle
with an auditor, they run the replay offline.

---

## What replay cannot do

Replay re-evaluates the policy engine. It does not:
- Re-run the tool handler (no side effects are reproduced)
- Reconstruct the original payload (not stored in the audit log)
- Verify network conditions at the time of the original decision

It answers the policy question: "given what we knew then, and what our policy says now,
do they agree?" That is the question that matters for security forensics and compliance.

---

## See also

- [Repository](https://github.com/sv-pro/safe-mcp-proxy)
- `safe_mcp_proxy/executor.py` — `replay()` implementation
- `safe_mcp_proxy/bundle_replay.py` — offline bundle replay
- `wiki/audit-replay.md` — concept page
- Previous post: audit-log-primitive — the log that makes replay possible
