After an incident, there are two different questions. "What happened?" requires an audit log. "Would our current policy have prevented this?" requires something more: deterministic replay.

In safe-mcp-proxy, executor.replay() takes a recorded audit entry and re-runs the policy engine against it. Same inputs — same tool, same taint flag, same schema hash — same output. If the policy changed since the original decision, the replayed result diverges. matches: false is a configuration drift signal.

This enables forensic investigation of policy evolution. A tool added to the allowlist after an incident? Original: ABSENT, replayed: ALLOW. A capability disabled after a policy review? Original: ALLOW, replayed: ABSENT. A schema mutated and never restored? Original: ALLOW on valid hash, replayed: DENY on drifted hash.

The bundle replay feature makes this offline. Export a snapshot of the manifest plus audit entries, share it with an auditor, replay the entire bundle without access to the live system. Forensic investigation without infrastructure.

The key property: determinism. The policy engine produces the same output for the same inputs, always. That is what makes replay trustworthy rather than approximate.

→ https://github.com/sv-pro/safe-mcp-proxy
