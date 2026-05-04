# `safe_mcp_proxy/scenarios/`

## Role

Registered, runnable test scenarios. Each scenario declares a tool, payload, source channel, and expected outcome. Scenarios are used by the API, the test suite, and the compare endpoint.

## Key symbols (in `__init__.py`)

| Name | Kind | Description |
|------|------|-------------|
| `Scenario` | dataclass | `name`, `description`, `tool`, `payload`, `source_channel`, `expected_decision`, `expected_rule`, `setup` |
| `SCENARIOS` | dict | Global registry: `{name: Scenario}` |
| `register` | function | Adds a `Scenario` to `SCENARIOS` |
| `get` | function | Returns scenario by name; raises `KeyError` if unknown |
| `names` | function | Returns list of registered scenario names |
| `run` | function | Executes a named scenario; returns `{scenario, result, expected_decision, expected_rule, matches}` |

## Registered scenarios

| Name | Tool | Source | Expected decision | Expected rule |
|------|------|--------|------------------|---------------|
| `benign_flow` | `read_file` | `cli` | `ALLOW` | `default_allow` |
| `prompt_injection` | `send_email` | `web` | `DENY` | `tainted_external_side_effect` |
| `poisoned_descriptor` | `read_file` | `cli` | `DENY` | `descriptor_drift` |
| `absent_tool` | `dangerous_exec` | `cli` | `ABSENT` | `tool_not_allowlisted` |

The `poisoned_descriptor` scenario has a `setup` function that mutates `read_file`'s schema before execution.

## Auto-registration

`__init__.py` imports all submodules at the bottom, triggering `register()` calls as a side effect.

## Used by

- [[src/api/index]] — `/scenarios/{name}/run` and `/compare`
- `tests/test_scenarios.py` — scenario validation tests

## See also

- [[src/safe_mcp_proxy/examples/index]] — standalone demos for the same scenarios
- [[absent-deny]] — the outcomes scenarios demonstrate
- [[policy-engine]] — all 4 scenarios exercise different policy paths
- [[world-manifest]] — scenarios execute against the default `world_manifest.yaml`
- [[provenance-taint]] — each scenario declares a `source_channel`; tainted ones test rule 4
- [[architecture]] — `scenarios.run()` exercises the full executor pipeline
