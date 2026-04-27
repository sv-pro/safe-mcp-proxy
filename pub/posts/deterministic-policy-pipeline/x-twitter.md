1/ The entire security enforcement logic in safe-mcp-proxy is 42 lines. Here's every decision path.

2/ Five rules, evaluated in fixed order. First match wins.
1. Not in allowlist → ABSENT
2. Capability disabled → ABSENT
3. Schema mutated → DENY
4. Tainted + external → DENY
5. Approval required → ASK
6. (all clear) → ALLOW

3/ The ordering is not arbitrary. ABSENT before DENY: a hidden tool can't trigger a taint check — it doesn't exist. DENY before ASK: tainted requests can't reach the approval gate.

4/ The policy engine is a pure function. Tool name, taint flag, schema hash, source channel in. (decision, rule) out. No state. No LLM. No randomness.

5/ Two implementations, identical decisions: Python (default) or OPA/Rego (for teams that want policy-as-code with formal auditing).

6/ A policy you can read in 42 lines is a policy you can audit. https://github.com/sv-pro/safe-mcp-proxy
