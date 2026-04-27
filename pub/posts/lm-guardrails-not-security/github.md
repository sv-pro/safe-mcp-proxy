# LLM Guardrails Are Not a Security Primitive

"We trained the model not to do that" is not a security guarantee. Here's why, and what deterministic enforcement looks like instead.

## The comparison

| Property | LLM guardrail | Deterministic policy |
|----------|--------------|----------------------|
| Determinism | No — same input can produce different output | Yes — same inputs, same decision |
| Bypassable | Yes — adversarial prompts, model updates | No — evaluates before model acts |
| Auditable | Difficult | Every decision logged with rule hit |
| Changes with model update | Yes | No |

## What the policy engine does

In [safe-mcp-proxy](https://github.com/sv-pro/safe-mcp-proxy), the policy engine runs **before** the model decides anything about tool calls. Five rules, evaluated in fixed order:

```
1. tool_not_allowlisted?   → ABSENT (model never knew it existed)
2. capability_not_allowed? → ABSENT
3. descriptor_drift?       → DENY
4. tainted + external?     → DENY
5. approval_required?      → ASK
```

The model's reasoning is irrelevant to steps 1-5. Even a fully compromised model cannot call a tool that isn't in the world.

## Why determinism matters

- **Testable:** `assert decide("send_email", taint=True) == DENY` — you can write this test. You cannot write a test for guardrails.
- **Auditable:** every decision is logged; past decisions can be replayed.
- **Model-independent:** upgrade the LLM, the policy doesn't change.

**See also:** [`docs/safe_skills_projection.md`](../../docs/safe_skills_projection.md) · [`policy_engine.py`](../../safe_mcp_proxy/policy_engine.py)
