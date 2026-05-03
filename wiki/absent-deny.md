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

**ASK** is a third distinct outcome, produced by rule 5 (`approval_required`). The tool is visible, the invocation is structurally valid, but execution is paused pending explicit human approval. ASK is provisional — it resolves to ALLOW (approved) or DENY (rejected) after the human decides. See [[ask-approval]] for the full lifecycle.

The response payload differs:
```json
// ABSENT
{"decision": "ABSENT", "rule": "tool_not_allowlisted", "result": {"error": "Action does not exist in this world"}}

// DENY
{"decision": "DENY", "rule": "tainted_external_side_effect", "result": {"error": "Denied by policy", "reason": "tainted_external_side_effect"}}
```

The ABSENT message (`"Action does not exist in this world"`) is the canonical string defined as `ABSENT_MESSAGE` in [[src/safe_mcp_proxy/executor]].

## See also

- [[policy-engine]] — the 6-path decision logic
- [[ask-approval]] — ASK: the third outcome (provisional, not terminal)
- [[world-manifest]] — where the allowlist and capability flags live
- [[provenance-taint]] — taint is the condition for DENY rule 4
- [[descriptor-drift]] — schema mutation is the condition for DENY rule 3
- [[src/safe_mcp_proxy/decision]] — the `Decision` enum
- [[src/safe_mcp_proxy/policy_engine]] — produces ABSENT/DENY/ASK results
- [[src/safe_mcp_proxy/registry]] — `get_tool()` returning `None` triggers ABSENT
- [[src/safe_mcp_proxy/executor]] — dispatches on decision; defines `ABSENT_MESSAGE`

---

## Open question: SIMULATE as a generalised meta-layer

> *Status: conceptual — not yet implemented. Captured here so it isn't lost.*

`SIMULATE` currently appears in two unrelated roles:

1. **Runtime flag** (`simulate_external=True`) — suppresses real external calls in tests/demos.
2. **Decision enum value** — returned by `GeminiPolicyGate` when ALLOW + simulate flag is active.

These two roles conflate a *policy decision* with a *runtime behaviour*. The deeper insight is that **ABSENT is itself a simulation** — the proxy fabricates a world in which a real tool does not exist. That makes ABSENT a special case of a broader concept: the proxy substituting a fake reality for the real one.

### Proposed taxonomy

| Mode | Current name | Description |
|------|-------------|-------------|
| `SIMULATE_ABSENCE` | `ABSENT` | Tool hidden — agent believes it doesn't exist |
| `SIMULATE_SUCCESS` | `simulate_external` flag | Mock success result instead of real call |
| `SIMULATE_FAILURE` | — | Mock error — deny without revealing policy reason; useful as a honeypot |
| `SIMULATE_DELAY` | — | Artificial latency — rate limiting, tripwire, cooling-off period |
| `SIMULATE_SANDBOX` | — | Real call executed in isolated environment |
| `SIMULATE_PARTIAL` | Atlassian `arg_rules` truncation | Filtered/truncated result (Confluence → 500 chars already does this) |

### Architectural choice

Two clean options:

**A. SIMULATE as an orthogonal Effect modifier (preferred)**

```
Decision = ALLOW | DENY | ABSENT | ASK          ← policy axis (unchanged)
Effect   = Execute | Simulate(SimMode)           ← runtime axis (new)
```

`ALLOW + Simulate(success)` = current `simulate_external`. ABSENT stays a policy decision.
Decision and Effect are separate concerns; no enum surgery required.

**B. SIMULATE as a first-class Decision, subsuming ABSENT**

```
Decision = ALLOW | DENY | SIMULATE(mode) | ASK
where ABSENT ≡ SIMULATE(absence)
```

Unifies all "reality substitution" under one concept, but breaks the clean six-rule policy engine and the "does not exist" principle.

Option A preserves the existing policy invariants and audit semantics; Option B is conceptually purer but requires wider refactoring. Neither has been implemented yet.
