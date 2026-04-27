# The Deterministic Policy Pipeline: Five Rules, Evaluated in Order

The policy engine in safe-mcp-proxy is 42 lines. It has no external dependencies, no
randomness, and no LLM in its path. Given the same inputs, it produces the same output.
Always.

Here is every decision path, in the order they are evaluated.

---

## The five rules

Every tool invocation passes through these checks. The first rule that matches wins.
No further checks are evaluated.

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

6. (none matched)
   → ALLOW / default_allow
```

Inputs to each invocation:
- `tool_name` — what the agent is trying to call
- `capability` — the tool's capability key from the registry
- `taint` — whether the request provenance is tainted (see taint-propagation)
- `side_effect_type` — `"read"`, `"internal"`, `"external"`, or `"unknown"`
- `descriptor_hash_valid` — whether the live schema matches the hash pinned at startup

---

## Why the ordering is not arbitrary

**ABSENT before DENY.** Rules 1 and 2 run before rules 3 and 4. A tool not in the
allowlist cannot trigger a descriptor check or a taint violation — it does not exist.
Checking DENY rules first would leak information: the denial message would reveal that
the tool exists, which the agent should not know.

**DENY before ASK.** Rule 4 (tainted external) runs before rule 5 (approval required).
A tainted request cannot reach the approval gate. Even if a capability is configured with
`requires_approval: true`, a tainted invocation is denied outright. Human approval does
not override taint.

**ALLOW is the last resort.** Rule 6 fires only if all five checks pass. The default is
allow-if-clean, not allow-if-not-explicitly-denied. But clean means: present, enabled,
untampered, untainted, and unapproved. That is a narrower set than it appears.

---

## Two implementations

**Python engine (default):** `PolicyEngine` in `policy_engine.py`. Pure Python, no
external dependencies. Wired by `build_executor()` in `main.py`.

**OPA engine:** `OPAPolicyEngine` in `opa_engine.py`. The same five rules implemented
in Rego, evaluated via OPA (subprocess or REST). Drop-in replacement — same `decide()`
signature. Same decisions for identical inputs. Useful for teams that want policy-as-code
with formal tooling and external audits.

Select via `policy_engine: opa` in `world_manifest.yaml` or `--engine opa` on the CLI.

---

## Inputs and outputs

The policy engine is a pure function. No state. No side effects.

```python
class PolicyEngine:
    def decide(
        self,
        tool_name: str,
        capability: str,
        taint: bool,
        side_effect_type: str,
        descriptor_hash_valid: bool,
    ) -> PolicyResult:
        ...
```

`PolicyResult` is a `(decision, rule_hit)` tuple. The executor dispatches on `decision`:
- `ALLOW` → call the handler (or simulate if external)
- `DENY` → return error; log denial
- `ABSENT` → return "Action does not exist in this world"; log absence
- `ASK` → create approval token; or DENY if BACKGROUND mode

---

## Why this matters for security

A policy engine you can read in 42 lines is a policy engine you can audit. The entire
decision logic fits in a single function. There is no hidden state, no configuration
that modifies behavior at runtime, no dependency on model output.

It is also testable in the most direct way: for every combination of inputs, assert the
expected output. The test suite includes 100-entry replay scenarios that verify
decisions are consistent across runs.

---

## See also

- [Repository](https://github.com/sv-pro/safe-mcp-proxy)
- `safe_mcp_proxy/policy_engine.py` — the implementation
- `safe_mcp_proxy/opa_engine.py` — OPA alternative
- `wiki/policy-engine.md` — concept page
- `wiki/absent-deny.md` — ABSENT and DENY in depth
- `wiki/provenance-taint.md` — source of the `taint` input
- `wiki/descriptor-drift.md` — source of the `descriptor_hash_valid` input
