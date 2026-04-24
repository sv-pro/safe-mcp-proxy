# `opa_engine.py`

## Role

OPA/Rego drop-in replacement for `PolicyEngine`. Evaluates the same 5 policy rules via the OPA binary (subprocess) or OPA REST server.

## Key symbols

| Name | Kind | Description |
|------|------|-------------|
| `OPAPolicyEngine` | class | Drop-in for `PolicyEngine` — identical `decide()` signature |
| `OPAPolicyEngine.__init__` | method | Takes `policy_path`, `allowlist`, `capability_map`, `evaluator`, `opa_url` |
| `OPAPolicyEngine.decide` | method | Assembles OPA input, evaluates, returns `PolicyResult` |
| `_eval_subprocess` | method | Runs `opa eval --data proxy.rego --input /dev/stdin` |
| `_eval_rest` | method | POSTs to OPA REST API at `opa_url` |

## Evaluator modes

| Mode | Mechanism | Requirement |
|------|-----------|-------------|
| `subprocess` (default) | `opa` binary via `subprocess.run` | OPA binary on PATH |
| `rest` | HTTP POST to OPA REST API | Running OPA server at `opa_url` |

If `evaluator="subprocess"` and `opa` is not on PATH, `__init__` raises `RuntimeError` immediately.

## OPA package

The Rego policy is evaluated at `data.safe_mcp_proxy.decision` (`_OPA_PACKAGE`). Default REST URL: `http://localhost:8181/v1/data/safe_mcp_proxy/decision`.

## Input → output

Input is built by [[src/safe_mcp_proxy/compiler]]'s `build_opa_input()`. Output is `{"decision": "ALLOW|DENY|ABSENT", "rule": "<rule_hit>"}`.

## Depends on

- [[src/safe_mcp_proxy/compiler]] — `build_opa_input()`
- [[src/safe_mcp_proxy/decision]] — `Decision` enum
- [[src/safe_mcp_proxy/policy_engine]] — `PolicyResult` dataclass

## Used by

- [[src/safe_mcp_proxy/main]] — `_build_policy_engine()` when `engine == "opa"`

## See also

- [[policy-engine]] — concept page; Python and OPA implementations described
- [[absent-deny]] — both evaluators produce ABSENT and DENY outcomes
- [[world-manifest]] — `allowlist` and `capability_map` passed in from compiled manifest
- [[descriptor-drift]] — `descriptor_hash_valid` is one of the inputs to `decide()`
- [[architecture]] — `OPAPolicyEngine` is an alternative stage 3 in the pipeline
- [[src/safe_mcp_proxy/policies/index]] — the Rego policy file
