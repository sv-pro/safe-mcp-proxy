# `safe_mcp_proxy/policies/`

## Role

OPA Rego policy files. `proxy.rego` is the canonical policy used by [[src/safe_mcp_proxy/opa_engine]] when `policy_engine: opa` is selected.

## Files

### `proxy.rego`

Implements the same 5 decision rules as the Python [[src/safe_mcp_proxy/policy_engine]], in the same priority order.

Package: `safe_mcp_proxy`  
Output path: `data.safe_mcp_proxy.decision`

Input schema:

| Field | Type | Description |
|-------|------|-------------|
| `tool_name` | string | Requested tool |
| `capability` | string | Capability key |
| `taint` | boolean | Tainted provenance flag |
| `side_effect_type` | string | `"external"` \| `"internal"` \| `"read"` \| `"unknown"` |
| `descriptor_hash_valid` | boolean | Schema hash validity |
| `allowlist` | array | Allowed tool names |
| `capability_map` | object | `{capability: bool}` |

Output: `{"decision": "ALLOW|DENY|ABSENT", "rule": "<rule_hit>"}`

Rule ordering mirrors Python engine exactly:
1. `tool_not_allowlisted` → ABSENT
2. `capability_not_allowed` → ABSENT
3. `descriptor_drift` → DENY
4. `tainted_external_side_effect` → DENY
5. `default_allow` (default rule) → ALLOW

### `proxy_test.rego`

OPA unit tests for `proxy.rego`.

## See also

- [[policy-engine]] — concept page; both implementations described
- [[absent-deny]] — the Rego rules directly implement ABSENT and DENY outcomes
- [[world-manifest]] — `allowlist` and `capability_map` flow in as OPA `input`
- [[provenance-taint]] — `input.taint` drives rule 4 in the Rego policy
- [[descriptor-drift]] — `input.descriptor_hash_valid` drives rule 3 in the Rego policy
- [[architecture]] — `proxy.rego` is the alternative stage 3 in the pipeline
- [[src/safe_mcp_proxy/opa_engine]] — the Python module that invokes this file
