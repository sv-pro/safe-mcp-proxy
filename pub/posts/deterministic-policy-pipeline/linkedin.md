The entire security enforcement logic in safe-mcp-proxy is 42 lines.

Five rules, evaluated in fixed order. First match wins. Same inputs, same decision, always.

The ordering is not arbitrary. ABSENT checks run before DENY checks — a hidden tool can't trigger a taint violation, because it doesn't exist. DENY checks run before the approval gate — a tainted request can't reach a human for approval. And ALLOW fires last, only when everything else is clean.

The policy engine is a pure function. No state. No side effects. No LLM in the path. Given tool name, taint flag, schema hash validity, and source channel — it returns a (decision, rule) tuple.

Two implementations, identical decisions: a Python version (default) and an OPA/Rego version for teams that want policy-as-code with formal tooling.

A policy you can read in 42 lines is a policy you can audit.

→ https://github.com/sv-pro/safe-mcp-proxy/blob/main/safe_mcp_proxy/policy_engine.py
