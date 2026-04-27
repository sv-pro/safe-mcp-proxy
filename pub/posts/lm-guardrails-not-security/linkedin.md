"We trained the model not to do that."

This is the most common answer to AI agent security questions. And it is not a security guarantee — it is a probabilistic claim.

LLM guardrails work until they don't. With the right adversarial prompt, the right injected context, or a new model version that behaves slightly differently, "the model refuses" becomes "the model complied."

The alternative is a deterministic policy engine. Not a smarter model. An enforcement layer that runs before the model makes any decision about tool calls.

In safe-mcp-proxy, the policy engine evaluates five rules in fixed order. Given a web-sourced request for send_email, the decision is always DENY — regardless of what the model says, regardless of model version, regardless of how sophisticated the injection is. The enforcement happens outside the model's reasoning path.

The key property is determinism: same inputs, same decision, always. You can write a unit test that asserts this. You cannot write a unit test for "the model will probably refuse."

Guardrails and policy engines are not alternatives — they're different layers. Only one of them can be proven correct.

→ 42 lines of enforcement: https://github.com/sv-pro/safe-mcp-proxy/blob/main/safe_mcp_proxy/policy_engine.py
