Most systems have an audit log. Few treat it as a security primitive.

The difference: an event log tells you what happened. A forensic audit log tells you what decision was made, which specific rule made it, what the system state was at that moment, and whether the decision would be the same today.

safe-mcp-proxy's audit log is append-only by design. Mode "a" on every write. No update mechanism. No delete. An audit log that can be modified is not an audit log — it is a history someone controls.

Every entry records: the tool name, the policy decision (ALLOW/DENY/ABSENT/ASK), the specific rule that fired, the taint flag, the source channel, and the SHA256 hash of the tool schema at that moment.

That last field — descriptor_hash — is the forensic anchor. If the schema changed between two invocations, you can see it in the hash difference. If you want to verify what schema was active during a past decision, the hash tells you.

When a capability requires approval, the log records two entries: the ASK (when the gate triggered) and the ALLOW or DENY (when the human decided). You can audit not just the outcome but the approval lifecycle.

→ https://github.com/sv-pro/safe-mcp-proxy
