# `demos/core/`

## Role

Standalone core demo scripts. Each script builds a full executor and runs one representative scenario, printing the result to stdout. `safe_mcp_proxy/examples/` now contains compatibility wrappers.

## Scripts

| File | Scenario | Expected outcome |
|------|----------|-----------------|
| `demos/core/benign_flow.py` | CLI reads a file | `ALLOW / default_allow` |
| `demos/core/prompt_injection.py` | Web-sourced request to send_email | `DENY / tainted_external_side_effect` |
| `demos/core/poisoned_descriptor.py` | Schema mutated before invocation | `DENY / descriptor_drift` |
| `demos/core/absent_tool_case.py` | Tool not in allowlist | `ABSENT / tool_not_allowlisted` |
| `demos/core/deterministic_replay.py` | Replay of a recorded audit entry | `matches: True` |

## Running

```bash
python -m demos.core.benign_flow
python -m demos.core.prompt_injection
python -m demos.core.poisoned_descriptor
python -m demos.core.absent_tool_case
```

## Difference from scenarios

These are standalone scripts that print output directly. The [[src/safe_mcp_proxy/scenarios/index]] package provides structured, registered scenarios that are callable from the API and test suite.

## See also

- [[src/safe_mcp_proxy/scenarios/index]] — registered scenario system
- [[absent-deny]] — the two outcomes these demos illustrate
- [[policy-engine]] — each demo exercises a different policy decision path
- [[provenance-taint]] — `prompt_injection.py` demonstrates taint-based DENY
- [[descriptor-drift]] — `poisoned_descriptor.py` demonstrates drift-based DENY
- [[world-manifest]] — demos load `world_manifest.yaml` via `build_executor()`
- [[audit-replay]] — each demo run appends entries to the audit log
- [[architecture]] — demos run the full executor pipeline end-to-end
