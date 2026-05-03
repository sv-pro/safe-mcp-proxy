# ABSENT vs DENY

ABSENT and DENY belong to different architectural layers. Understanding the distinction requires knowing which layer each lives in.

## The three-layer model

```
Layer 1 — Ontology    Does this action exist in this world?
Layer 2 — Policy      Is this action permitted in context?
Layer 3 — Effect      How is reality presented to the agent?
```

**ABSENT** is a Layer 1 (Ontology) outcome. The action is not part of this world's ontology — it was never offered to the agent. This is not a refusal; it is an absence.

**DENY** is a Layer 2 (Policy) outcome. The action exists and was offered, but a specific invocation was rejected by policy.

This maps to the project's core principle:

> "Some actions are denied. Others do not exist."

Effect Virtualization (Layer 3) is handled separately — see [[effect-virtualization]].

## Why it exists

MCP enables runtime tool discovery, which means an agent could theoretically be manipulated — via prompt injection — into calling any tool the server exposes. ABSENT eliminates this attack surface at the root: if a tool is not in the world manifest's `allowed_tools`, it is invisible. The agent cannot be tricked into calling something it has never seen.

DENY handles a different threat: a tool is legitimately in the world, but a particular invocation violates policy — the request came from an untrusted channel (taint), or the tool's schema was mutated at runtime (descriptor drift).

## How they work

Both outcomes are produced by [[policy-engine]] and returned as the `decision` field in the response JSON. Rules 1–2 are ontological (ABSENT); rules 3–4 are policy (DENY).

**ABSENT** is produced by rules 1 and 2:
- `tool_not_allowlisted` — tool name not in the registry's allowlist
- `capability_not_allowed` — capability flag is `false` in `capability_map`

**DENY** is produced by rules 3 and 4:
- `descriptor_drift` — current schema SHA256 ≠ stored hash
- `tainted_external_side_effect` — tainted provenance + external side-effect tool

**ASK** is a third distinct outcome (rule 5: `approval_required`). The tool is visible, the invocation is structurally valid, but execution is paused pending explicit human approval. ASK is provisional — it resolves to ALLOW (approved) or DENY (rejected). See [[ask-approval]].

The response payload differs:
```json
// ABSENT
{"decision": "ABSENT", "rule": "tool_not_allowlisted", "result": {"error": "Action does not exist in this world"}}

// DENY
{"decision": "DENY", "rule": "tainted_external_side_effect", "result": {"error": "Denied by policy", "reason": "tainted_external_side_effect"}}
```

The ABSENT message (`"Action does not exist in this world"`) is the canonical string defined as `ABSENT_MESSAGE` in [[src/safe_mcp_proxy/executor]].

## See also

- [[effect-virtualization]] — Layer 3: how reality is presented to the agent after a policy decision
- [[policy-engine]] — the 6-path decision logic (rules 1–2 ontological, rules 3–4 policy)
- [[ask-approval]] — ASK: the third outcome (provisional, not terminal)
- [[world-manifest]] — where the allowlist and capability flags live
- [[provenance-taint]] — taint is the condition for DENY rule 4
- [[descriptor-drift]] — schema mutation is the condition for DENY rule 3
- [[src/safe_mcp_proxy/decision]] — the `Decision` enum
- [[src/safe_mcp_proxy/policy_engine]] — produces ABSENT/DENY/ASK results
- [[src/safe_mcp_proxy/registry]] — `get_tool()` returning `None` triggers ABSENT
- [[src/safe_mcp_proxy/executor]] — dispatches on decision; defines `ABSENT_MESSAGE`
