# `demos/core/`

Minimal runnable scripts that exercise one policy path at a time.

| Script | Scenario | Expected outcome |
|--------|----------|------------------|
| `benign_flow.py` | Clean CLI `read_file` request | `ALLOW / default_allow` |
| `prompt_injection.py` | Web-sourced `send_email` request | `DENY / tainted_external_side_effect` |
| `poisoned_descriptor.py` | Mutated `read_file` schema before invocation | `DENY / descriptor_drift` |
| `absent_tool_case.py` | `dangerous_exec` outside world allowlist | `ABSENT / tool_not_allowlisted` |
| `ask_modes.py` | `send_email` under INTERACTIVE and BACKGROUND modes | `ASK`, then background `DENY` |
| `deterministic_replay.py` | Replay of generated audit decisions | Recorded and replayed decisions match |
| `demo_all.py` | Legacy combined four-scenario demo | Mixed ALLOW/DENY/ABSENT output |

Run examples:

```bash
python -m demos.core.prompt_injection
python -m demos.core.absent_tool_case
python -m demos.core.deterministic_replay
```

These scripts are human-facing wrappers around the same executor pipeline tested
by `safe_mcp_proxy/scenarios/` and the API scenario endpoints.
