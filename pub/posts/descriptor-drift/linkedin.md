A supply-chain attack doesn't need to replace your tool. It just needs to modify the schema after startup.

The agent still sees read_file. The allowlist check still passes. But the underlying schema has changed — maybe the description now contains injection instructions, maybe there's a new parameter for exfiltration. The agent has no way to know.

Descriptor drift detection closes this attack vector. In safe-mcp-proxy, every tool stores a SHA256 hash of its schema at registration. Before each invocation, the hash is recomputed and compared to the stored value. If they don't match — DENY / descriptor_drift.

The hash uses normalized JSON (sorted keys, no extra whitespace) so the same schema always produces the same hash regardless of insertion order. Deterministic input, deterministic output.

The hash also appears in every audit log entry. This means you can verify which schema was active at any past decision, detect when a schema changed between two entries, and replay past decisions to check if drift would have changed the outcome.

Run the demo: python -m safe_mcp_proxy.examples.poisoned_descriptor → DENY / descriptor_drift

→ https://github.com/sv-pro/safe-mcp-proxy
