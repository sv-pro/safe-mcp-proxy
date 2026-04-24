# `policy_engine.py`

## Role

Pure Python decision logic. Takes 5 inputs, evaluates 5 ordered rules, returns a `PolicyResult`. No side effects, no I/O.

## Key symbols

| Name | Kind | Description |
|------|------|-------------|
| `PolicyResult` | frozen dataclass | `(decision: Decision, rule_hit: str)` |
| `PolicyEngine` | class | Stateful engine holding the allowlist and capability_map |
| `PolicyEngine.__init__` | method | Takes `allowlist: Iterable[str]`, `capability_map: Dict[str, bool]` |
| `PolicyEngine.decide` | method | Evaluates 5 rules and returns `PolicyResult` |

## `decide()` signature

```python
def decide(
    self,
    tool_name: str,
    capability: str,
    taint: bool,
    side_effect_type: str,
    descriptor_hash_valid: bool,
) -> PolicyResult
```

## Rule evaluation order

```
1. tool_name not in self.allowlist          → ABSENT / tool_not_allowlisted
2. not self.capability_map.get(capability)  → ABSENT / capability_not_allowed
3. not descriptor_hash_valid                → DENY   / descriptor_drift
4. taint and side_effect_type == "external" → DENY   / tainted_external_side_effect
5. (default)                                → ALLOW  / default_allow
```

## Depends on

- [[src/safe_mcp_proxy/decision]] — `Decision` enum

## Used by

- [[src/safe_mcp_proxy/executor]] — `policy_engine.decide()`
- [[src/safe_mcp_proxy/main]] — instantiated in `_build_policy_engine()`

## See also

- [[policy-engine]] — concept page with full design rationale
- [[absent-deny]] — ABSENT and DENY are the two failure outcomes this module produces
- [[provenance-taint]] — `taint` input comes from `Provenance.tainted`
- [[descriptor-drift]] — `descriptor_hash_valid` input drives rule 3
- [[world-manifest]] — `allowlist` and `capability_map` constructor args come from the compiled manifest
- [[architecture]] — PolicyEngine is stage 3 in the fixed pipeline
- [[src/safe_mcp_proxy/opa_engine]] — alternative OPA implementation with same interface
