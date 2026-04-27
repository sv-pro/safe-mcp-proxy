1/ Most systems have an audit log. Few treat it as a security primitive. Here's what that distinction means in practice.

2/ An event log: "send_email was called at 12:00." A forensic audit log: "send_email was called at 12:00, DENIED by tainted_external_side_effect, taint=true, source_channel=web, schema hash=a3f8c21d."

3/ The audit log in safe-mcp-proxy is append-only. Mode "a" on every write. No update mechanism. An audit log that can be modified is not an audit log.

4/ Every entry records the specific rule that fired. Not just "denied" — "denied because tainted_external_side_effect." You know exactly why every decision was made.

5/ The descriptor_hash field: SHA256 of the tool schema at decision time. If two entries for the same tool have different hashes, the schema mutated between them. You can see exactly when.

6/ ASK creates two entries: one when the approval gate triggered, one when the human decided (approved or rejected). Auditable lifecycle, not just auditable outcome.

7/ TraceStore wraps the JSONL for queries: store.filter(decision="DENY", tool="send_email", since=...) — no database layer required.

8/ https://github.com/sv-pro/safe-mcp-proxy
