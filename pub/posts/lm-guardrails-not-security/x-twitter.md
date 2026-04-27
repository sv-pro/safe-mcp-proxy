1/ "We trained the model not to do that" is not a security guarantee. Thread on why — and what deterministic enforcement looks like instead.

2/ LLM guardrails are probabilistic. Same input, different context → different output. Adversarial prompts, model updates, injected instructions — all of these can flip a "refusal" into a "compliance."

3/ The alternative: a policy engine that runs before the model makes any decision about tool calls. Not smarter alignment. A different layer.

4/ In safe-mcp-proxy: 5 rules, fixed order. Given a web-sourced request for send_email → DENY. Always. Regardless of what the model says. The enforcement is outside the model's reasoning path.

5/ Why determinism matters: same inputs → same decision → testable. You can write: assert decide("send_email", taint=True) == DENY. You cannot write a test for "the model will probably refuse."

6/ Also: auditable. Every decision is logged. Past decisions can be replayed against current policy. You can prove consistency across time.

7/ Guardrails and policy engines are not alternatives. They're different layers. Guardrails for output quality. Policy engines for access control. Only one of them can be proven correct.

8/ The entire enforcement logic: 42 lines. https://github.com/sv-pro/safe-mcp-proxy/blob/main/safe_mcp_proxy/policy_engine.py
