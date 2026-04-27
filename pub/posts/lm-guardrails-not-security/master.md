# LLM Guardrails Are Not a Security Primitive

The common answer to "how do you prevent your AI agent from doing something harmful?" is:
*we trained the model not to.* Or: *we added a system prompt that tells it to refuse.*

These are guardrails. They are not security primitives.

The distinction matters operationally, not philosophically.

---

## What a guardrail does

A guardrail says: "the model will probably refuse this."

*Probably.* With the right prompt, the right context, the right adversarial input, models
that "refuse harmful actions" can be coaxed into executing them. This is not a theoretical
concern — jailbreaks are documented, reproducible, and often transferable across model
versions.

More precisely:

| Property | LLM guardrail | Deterministic policy |
|----------|--------------|----------------------|
| Mechanism | Model training + prompt | Code-enforced rule |
| Determinism | No — same input can produce different output | Yes — same inputs, same decision |
| Bypassable | Yes — adversarial prompts, model updates, context manipulation | No — evaluates before model can act |
| Auditable | Difficult — model is a black box | Yes — every decision logged with rule |
| Changes with model update | Yes | No — policy is separate from model |

A guardrail depends on the model's behavior at inference time. A policy engine runs in
the execution layer — *before the model decides anything about tool calls.*

---

## The attack surface is not the model

Prompt injection attacks don't try to convince the model that harmful actions are benign.
They embed instructions in data the model reads — web pages, emails, documents — and
rely on the model treating those instructions as legitimate.

If the model reads a web page that says *"call send_email with this payload,"* the
question is not whether the model is aligned enough to refuse. The question is: *can the
model even access `send_email` from this context?*

A guardrail answers the alignment question. A policy engine answers the access question.
The access question is prior.

---

## What deterministic enforcement looks like

In safe-mcp-proxy, the policy engine runs between the request and the execution layer.
It evaluates five rules in fixed order, independent of anything the model says:

1. Is the tool in the allowlist? If not → ABSENT. The model never learned it exists.
2. Is the capability enabled? If not → ABSENT.
3. Has the schema been mutated since startup? If yes → DENY.
4. Did this request originate from a tainted channel and target an external tool? → DENY.
5. Does this capability require human approval? → ASK.

The model's opinion about whether to call the tool is irrelevant to steps 1-5. The model
could be completely compromised — convinced by injection to call anything — and the policy
still holds, because the enforcement happens outside the model's reasoning path.

---

## The key property: determinism

Determinism means: given the same inputs (tool name, source channel, schema hash, taint
flag), the policy always produces the same output (decision + rule).

This matters for three reasons:

**Auditability:** Every decision is logged. The log can be replayed. If you want to know
whether a past decision was correct, replay it against the current policy. If they don't
match, the policy changed — you can see exactly when and how.

**Testability:** You can write unit tests that assert specific decisions for specific
inputs. "Given a web-sourced request for `send_email`, the decision must be DENY." This
test will pass or fail deterministically. You cannot write this test for a guardrail.

**Independence from model updates:** When you upgrade your LLM, your policy doesn't change.
When your policy changes, your model doesn't have to retrain. They are separate concerns,
separated at the architecture level.

---

## Guardrails have their place

This is not an argument that LLM safety training is useless. It is an argument that it
is not sufficient as a security control.

Guardrails are defense-in-depth for the model's output: they reduce the probability that
a model will produce harmful content in normal operation. They are valuable for that.

Policy engines are the execution layer control: they enforce access rules regardless of
what the model decides. They are necessary for security guarantees.

The two are not alternatives. They are different layers. Only one of them can be tested,
audited, and proven deterministic.

---

## See also

- [Repository](https://github.com/sv-pro/safe-mcp-proxy)
- `docs/safe_skills_projection.md` — the comparison table this post expands
- `safe_mcp_proxy/policy_engine.py` — 42 lines that replace probabilistic guardrails
- `wiki/policy-engine.md` — the six decision paths
