# `demos/`

## Role

Canonical home for runnable safe-mcp-proxy demos. Demo code was consolidated
here from older locations such as `safe_mcp_proxy/examples/`, top-level
`demo.py`, top-level `run_demo.py`, `examples/safe_skills_demo/`, `docs/demo/`,
and `docs/notebooks/`.

The old entry points remain as compatibility wrappers. New demos should be
added under `demos/`.

## Layout

| Path | Purpose |
|------|---------|
| `demos/core/` | Minimal policy-path demos: ALLOW, DENY, ABSENT, ASK, descriptor drift, deterministic replay |
| `demos/integrations/` | Runtime integration demos for Claude Code, Gemini, and Atlassian MCP |
| `demos/product/dashboard/` | Dashboard/API smoke demo and one-click FastAPI launcher |
| `demos/narratives/zombieagent/` | Rich terminal narrative for support-ticket taint tracking and world lockdown |
| `demos/safe_skills/` | Safe Skills Projection demo: unsafe skill discovery vs projected capabilities |
| `demos/mcpzero/` | MCPZero launcher wrapper and notebook walkthrough assets |
| `demos/assets/` | VHS tapes and generated media for docs/README demos |

## Demo Catalog

| Demo | Value | Canonical command |
|------|-------|-------------------|
| Core benign flow | Clean read path | `python -m demos.core.benign_flow` |
| Core prompt injection | Tainted external side effect denied | `python -m demos.core.prompt_injection` |
| Core descriptor drift | Runtime schema mutation denied | `python -m demos.core.poisoned_descriptor` |
| Core absent tool | Hidden tool returns ABSENT | `python -m demos.core.absent_tool_case` |
| ASK modes | Interactive approval vs background DENY | `python -m demos.core.ask_modes` |
| Deterministic replay | Audit replay stability | `python -m demos.core.deterministic_replay` |
| Claude Code | MCP tool surface control and upstream forwarding | `python -m demos.integrations.claude_code.demo` |
| Gemini | Baseline exfiltration vs protected ontological absence | `python -m demos.integrations.gemini.demo` |
| Atlassian | Confluence-to-Jira raw data-flow block | `python -m demos.integrations.atlassian.demo` |
| Dashboard | Generates mixed audit decisions and verifies dashboard endpoints | `python -m demos.product.dashboard.demo` |
| Web launcher | Starts FastAPI and opens the dashboard | `python -m demos.product.dashboard.web_launcher` |
| ZombieAgent | Three-act support-ticket exfiltration narrative | `bash demos/narratives/zombieagent/run.sh` |
| Safe Skills | Skills supply-chain projection proof | `python -m demos.safe_skills.run_with_proxy` |
| MCPZero | Baseline vs protected attack-corpus comparison | `python -m mcpzero.demo` |

## Compatibility Wrappers

These legacy commands intentionally continue to work:

```bash
python demo.py
python run_demo.py
python -m safe_mcp_proxy.examples.prompt_injection
python -m examples.safe_skills_demo.run_with_proxy
bash demos/run_demo.sh
```

Compatibility wrappers are thin delegators. They should not grow new demo logic.

## Shared Inputs

`attacks/` remains a top-level shared corpus. It is used by MCPZero, tests, and
scenario APIs, but is not itself a runnable demo directory.

World manifests remain in `world_manifest.yaml`, `worlds/`,
`safe_mcp_proxy/config/worlds/`, and `manifests/` because they are runtime
policy inputs, not demo-only assets.

## See also

- [[src/safe_mcp_proxy/examples/index]] — compatibility wrapper package
- [[src/mcpzero/index]] — MCPZero framework package
- [[src/attacks/index]] — attack corpus
- [[audit-replay]] — demo trace seeding and replay
