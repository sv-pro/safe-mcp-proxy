# `safe_mcp_proxy/examples/`

## Role

Standalone demo scripts. Each script builds a full executor and runs one representative scenario, printing the result to stdout.

## Scripts

| File | Scenario | Expected outcome |
|------|----------|-----------------|
| `benign_flow.py` | CLI reads a file | `ALLOW / default_allow` |
| `prompt_injection.py` | Web-sourced request to send_email | `DENY / tainted_external_side_effect` |
| `poisoned_descriptor.py` | Schema mutated before invocation | `DENY / descriptor_drift` |
| `absent_tool_case.py` | Tool not in allowlist | `ABSENT / tool_not_allowlisted` |
| `deterministic_replay.py` | Replay of a recorded audit entry | `matches: True` |

## Running

```bash
python -m safe_mcp_proxy.examples.benign_flow
python -m safe_mcp_proxy.examples.prompt_injection
python -m safe_mcp_proxy.examples.poisoned_descriptor
python -m safe_mcp_proxy.examples.absent_tool_case
```

## Difference from scenarios

These are standalone scripts that print output directly. The [[src/safe_mcp_proxy/scenarios/index]] package provides structured, registered scenarios that are callable from the API and test suite.

## See also

- [[src/safe_mcp_proxy/scenarios/index]] — registered scenario system
- [[absent-deny]] — the two outcomes these demos illustrate
