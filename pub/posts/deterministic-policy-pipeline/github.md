# The Deterministic Policy Pipeline: Five Rules, Evaluated in Order

The [safe-mcp-proxy](https://github.com/sv-pro/safe-mcp-proxy) policy engine is 42 lines. No external dependencies. No LLM. Same inputs → same output.

## The decision paths

```
1. tool_name not in allowlist           → ABSENT / tool_not_allowlisted
2. capability_map[capability] == False  → ABSENT / capability_not_allowed
3. descriptor_hash_valid == False       → DENY   / descriptor_drift
4. taint AND side_effect_type=="external" → DENY / tainted_external_side_effect
5. capability in approval_required      → ASK    / approval_required
6. (none matched)                       → ALLOW  / default_allow
```

First match wins. No further checks evaluated.

## Why the ordering matters

- **ABSENT before DENY:** A hidden tool cannot trigger a taint violation or schema check — it doesn't exist. Reversing this would leak existence.
- **DENY before ASK:** A tainted request cannot reach the approval gate. Human approval doesn't override taint.
- **ALLOW is last:** Only fires if all five checks pass.

## Two implementations, identical decisions

```bash
# Python (default)
python -m safe_mcp_proxy.main --engine python ...

# OPA/Rego (drop-in)
python -m safe_mcp_proxy.main --engine opa ...
```

Or set `policy_engine: opa` in `world_manifest.yaml`.

**See also:** [`wiki/policy-engine.md`](../../wiki/policy-engine.md) · [`policy_engine.py`](../../safe_mcp_proxy/policy_engine.py)
