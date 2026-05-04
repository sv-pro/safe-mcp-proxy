# Core Demos

Minimal scripts that exercise one policy path each.

| Script | Demonstrates | Expected result | Command |
|---|---|---|---|
| `benign_flow.py` | Clean CLI read | `ALLOW / default_allow` | `python -m demos.core.benign_flow` |
| `prompt_injection.py` | Tainted web request to external side-effect tool | `DENY / tainted_external_side_effect` | `python -m demos.core.prompt_injection` |
| `poisoned_descriptor.py` | Runtime tool schema mutation | `DENY / descriptor_drift` | `python -m demos.core.poisoned_descriptor` |
| `absent_tool_case.py` | Tool outside the world allowlist | `ABSENT / tool_not_allowlisted` | `python -m demos.core.absent_tool_case` |
| `ask_modes.py` | Human approval in interactive vs background mode | `ASK`, then background `DENY` | `python -m demos.core.ask_modes` |
| `deterministic_replay.py` | Audit replay stability | All recorded and replayed decisions match | `python -m demos.core.deterministic_replay` |
| `demo_all.py` | Legacy combined four-scenario output | Mixed `ALLOW`, `DENY`, `ABSENT` | `python -m demos.core.demo_all` |
