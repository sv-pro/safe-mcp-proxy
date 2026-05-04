1/ A supply-chain attack doesn't need to replace your MCP tool. Just modify the schema after startup. The allowlist check still passes. But descriptor drift detection catches it.

2/ In safe-mcp-proxy, every tool stores a SHA256 hash of its schema at registration time. Before each invocation, the hash is recomputed and compared.

3/ If the schema changed: DENY / descriptor_drift. No matter where the request came from. No matter if the taint check would have passed. Schema integrity is checked first.

4/ The hash uses normalized JSON (sort_keys=True) — same schema, same hash, always. Deterministic input, deterministic output.

5/ The hash also appears in every audit entry. You can verify which schema was active at any past decision, and detect drift between entries.

6/ Demo: python -m demos.core.poisoned_descriptor → DENY / descriptor_drift

7/ The attack scenario is formalized in attacks/tool_chain.yaml. With the proxy: blocked at first call after mutation. Without: silent schema compromise.

8/ https://github.com/sv-pro/safe-mcp-proxy
