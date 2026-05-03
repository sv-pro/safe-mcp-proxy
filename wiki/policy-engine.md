# Policy Engine

Six deterministic decision paths evaluated in fixed priority order. Same inputs always produce the same output. No LLM in the enforcement path.

The policy engine covers **Layer 2 (Policy)** of the three-layer model. Layer 1 (Ontology) is handled by the Registry; Layer 3 (Effect Virtualization) is handled by the Executor. See [[architecture]] for the full pipeline.

## What it is

The `PolicyEngine` class (`policy_engine.py`) implements the core decision logic. It takes five inputs and returns a `PolicyResult(decision, rule_hit)` tuple.

Inputs:
- `tool_name` — the requested tool
- `capability` — the tool's capability key
- `taint` — whether the request provenance is tainted
- `side_effect_type` — `"read"`, `"internal"`, `"external"`, or `"unknown"`
- `descriptor_hash_valid` — whether the tool's current schema matches its pinned hash

## Decision paths (evaluated in order)

```
1. tool_name not in allowlist
   → ABSENT / tool_not_allowlisted

2. capability_map[capability] == False
   → ABSENT / capability_not_allowed

3. descriptor_hash_valid == False
   → DENY / descriptor_drift

4. taint == True AND side_effect_type == "external"
   → DENY / tainted_external_side_effect

5. capability in approval_required
   → ASK / approval_required

6. (none of the above)
   → ALLOW / default_allow
```

Rules 1–2 are **ontological** (Layer 1): they determine existence, not permission. Rules 3–4 are **policy** (Layer 2): they evaluate the context of an existing action. Rule 5 produces ASK. Only if all five checks pass does the request ALLOW.

The ordering is critical: ABSENT checks run before DENY checks, and DENY checks run before ASK. A tool not in the allowlist cannot trigger a taint violation or an approval request — it simply does not exist.

## Two implementations

**Python engine** (default): `PolicyEngine` in `policy_engine.py`. Pure Python, no external dependencies. Selected when `policy_engine: python` in the manifest or via `--engine python`.

**OPA engine**: `OPAPolicyEngine` in `opa_engine.py`. Evaluates the same 5 rules using the Rego policy at `safe_mcp_proxy/policies/proxy.rego`. Drop-in replacement — same `decide()` signature. Selected via `policy_engine: opa` in the manifest or `--engine opa`. Supports `subprocess` and `rest` evaluator modes.

Both implementations produce identical decisions for the same inputs. The Rego policy mirrors the Python ordering exactly.

## See also

- [[absent-deny]] — Ontology (Layer 1) and Policy (Layer 2) decisions
- [[effect-virtualization]] — Layer 3: how reality is presented after a policy decision
- [[ask-approval]] — the ASK decision: approval lifecycle, execution modes, API endpoints
- [[provenance-taint]] — source of the `taint` input
- [[descriptor-drift]] — source of the `descriptor_hash_valid` input
- [[src/safe_mcp_proxy/policy_engine]] — Python implementation
- [[src/safe_mcp_proxy/opa_engine]] — OPA implementation
- [[src/safe_mcp_proxy/policies/index]] — Rego policy file
- [[src/safe_mcp_proxy/executor]] — calls `policy_engine.decide()` on every invocation
- [[src/safe_mcp_proxy/registry]] — supplies the allowlist
- [[src/safe_mcp_proxy/compiler]] — supplies the `capability_map` and `approval_required` set
