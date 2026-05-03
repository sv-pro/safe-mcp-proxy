# Effect Virtualization

Effect Virtualization is the third architectural layer of Agent Hypervisor. It sits after ontology resolution and policy resolution and answers a different question from both.

> *In what reality does this action execute?*

## The three-layer model

```
Layer 1 — Ontology    Does this action exist in this world?   → ABSENT / PRESENT
Layer 2 — Policy      Is this action permitted in context?    → ALLOW / DENY / ASK
Layer 3 — Effect      How is reality presented to the agent?  → effect_mode
```

Ontology and policy answer *whether* an action runs. Effect Virtualization answers *how* it runs — and what the agent perceives as the outcome.

## Effect modes

```yaml
effect_mode:
  - EXECUTE    # real execution, unmodified
  - SIMULATE   # synthetic result, no real side effect
  - PROXY      # indirect or deferred execution
  - SANITIZE   # result filtered or redacted
  - TRUNCATE   # result shortened to a safe length
  - DEFER      # execution delayed pending a condition
```

These are orthogonal to policy decisions. The same decision can pair with different effect modes:

```yaml
# Real execution
decision: ALLOW
effect_mode: EXECUTE

# Synthetic result — agent perceives success, no side effect occurs
decision: ALLOW
effect_mode: SIMULATE

# Filtered result — agent sees a constrained view
decision: ALLOW
effect_mode: TRUNCATE
```

## Why SIMULATE is not a policy decision

Placing SIMULATE in the `Decision` enum conflates two independent axes. The correct model:

```
# Correct
decision: ALLOW         ← policy layer
effect_mode: SIMULATE   ← effect layer

# Incorrect
decision: SIMULATE      ← mixes policy with execution semantics
```

DENY teaches the attacker where a boundary exists. Each DENY provides a boundary-learning signal:

```
attempt → DENY → adaptation → probing
```

SIMULATE removes that signal entirely. The attacker receives a plausible success response and has no basis for adaptation:

```
attempt → simulated success → no adaptation
```

This is the primary security motivation for Effect Virtualization: deception is sometimes a stronger defence than refusal.

## What currently exists

| Concept | Current implementation |
|---------|----------------------|
| EXECUTE | `registry.execute_tool()` or upstream call |
| SIMULATE | `simulate_external=True` flag + `simulate_external_action()` in `simulate.py` |
| TRUNCATE | Atlassian `arg_rules` — Confluence page truncated to 500 chars |
| PROXY | Atlassian passthrough → `pending_approval` state |

SIMULATE and TRUNCATE are already implemented; they are not yet modelled as a unified layer with a named `effect_mode` field.

## Relationship to sandboxing

These are distinct concepts with different scope:

```
Sandbox:
  execution:  real (in isolated environment)
  effects:    limited by container boundaries

Simulation:
  execution:  virtualized
  effects:    synthetic or absent
```

A sandbox controls *where* execution happens. Effect Virtualization controls *what the agent perceives* happened.

## Relationship to testing mocks

SIMULATE resembles test mocks and stubs in mechanics, but differs in intent: test mocks exist only in test suites. Effect Virtualization is a production runtime primitive. The proxy turns the runtime into a continuously virtualized execution environment — the agent cannot distinguish a simulated response from a real one.

## Current status

SIMULATE and TRUNCATE are implemented but not yet modelled as a unified `effect_mode` field. The full effect mode taxonomy (EXECUTE / SIMULATE / PROXY / SANITIZE / TRUNCATE / DEFER) is the target architecture; current code partially realises it.

The `Decision` enum currently contains `SIMULATE` as a value (used by `GeminiPolicyGate`). This is a known inconsistency with the three-layer model; it should eventually move to a separate `effect_mode` field.

## See also

- [[absent-deny]] — Ontology (Layer 1) and Policy (Layer 2) decisions
- [[policy-engine]] — the 6 deterministic policy rules (Layer 2)
- [[architecture]] — full pipeline including Effect Virtualization
- [[src/safe_mcp_proxy/simulate]] — current SIMULATE implementation
- [[src/safe_mcp_proxy/decision]] — `Decision` enum (contains SIMULATE; to be refactored)
