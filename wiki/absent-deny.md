# ABSENT vs DENY

The core semantic distinction of safe-mcp-proxy. Two different failure modes, each with a distinct meaning.

## What they are

**ABSENT** — the tool or capability does not exist in this world. It was never offered to the agent. The agent has no knowledge of it.

**DENY** — a visible action was blocked by policy. The tool was in the agent's world, but a specific invocation was rejected.

This maps to the project's core principle:

> "Some actions are denied. Others do not exist."

## Why it exists

MCP enables runtime tool discovery, which means an agent could theoretically be manipulated — via prompt injection — into calling any tool the server exposes. ABSENT eliminates this attack surface at the root: if a tool is not in the world manifest's `allowed_tools`, it is invisible. The agent cannot be tricked into calling something it has never seen.

DENY handles a different threat: a tool is legitimately in the world, but a particular invocation violates policy — the request came from an untrusted channel (taint), or the tool's schema was mutated at runtime (descriptor drift).

## How they work

Both outcomes are produced by [[policy-engine]] and returned as the `decision` field in the response JSON.

**ABSENT** is produced by rules 1 and 2 (evaluated before any DENY checks):
- `tool_not_allowlisted` — tool name not in the registry's allowlist
- `capability_not_allowed` — capability flag is `false` in `capability_map`

**DENY** is produced by rules 3 and 4:
- `descriptor_drift` — current schema SHA256 ≠ stored hash
- `tainted_external_side_effect` — tainted provenance + external side-effect tool

The response payload differs:
```json
// ABSENT
{"decision": "ABSENT", "rule": "tool_not_allowlisted", "result": {"error": "Action does not exist in this world"}}

// DENY
{"decision": "DENY", "rule": "tainted_external_side_effect", "result": {"error": "Denied by policy", "reason": "tainted_external_side_effect"}}
```

The ABSENT message (`"Action does not exist in this world"`) is the canonical string defined as `ABSENT_MESSAGE` in [[src/safe_mcp_proxy/executor]].

## See also

- [[policy-engine]] — the 5-path decision logic
- [[world-manifest]] — where the allowlist and capability flags live
- [[provenance-taint]] — taint is the condition for DENY rule 4
- [[descriptor-drift]] — schema mutation is the condition for DENY rule 3
- [[src/safe_mcp_proxy/decision]] — the `Decision` enum
