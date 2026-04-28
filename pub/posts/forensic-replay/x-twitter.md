1/ After an incident: "what happened?" requires an audit log. "Would our policy have prevented this?" requires deterministic replay.

2/ executor.replay(audit_entry) re-runs the policy engine against a recorded decision. Same inputs → same output. If the manifest changed: matches: false.

3/ matches: false is a configuration drift signal. Tool added to allowlist after incident → original: ABSENT, replayed: ALLOW. Capability disabled → original: ALLOW, replayed: ABSENT.

4/ Schema drift shows up too. If a tool's schema was mutated and never restored, the original passes the hash check; the replay denies with descriptor_drift.

5/ Bundle replay: export manifest + audit entries as an offline snapshot. Share with an auditor. Replay without access to the live system.

6/ replayer = BundleReplayer(bundle_path) / mismatches = [r for r in replayer.replay_all() if not r["matches"]]

7/ The key property: determinism. Same inputs, same decision, always. That's what makes replay trustworthy rather than approximate.

8/ https://github.com/sv-pro/safe-mcp-proxy
