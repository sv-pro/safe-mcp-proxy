# Demo Catalog

This directory is the canonical home for runnable safe-mcp-proxy demos.

Compatibility wrappers remain at older paths such as `safe_mcp_proxy/examples/`,
`demo.py`, `run_demo.py`, and `examples/safe_skills_demo/`, but new demo work
should live here.

## Quick Pick

| Demo | Value | Command |
|---|---|---|
| Core policy paths | Smallest proof of `ALLOW`, `DENY`, `ABSENT`, `ASK`, and replay behavior | `python -m demos.core.prompt_injection` |
| Claude Code integration | Proves MCP tool-surface control and upstream forwarding | `python -m demos.integrations.claude_code.demo` |
| Gemini integration | Shows baseline exfiltration vs protected ontological absence | `python -m demos.integrations.gemini.demo` |
| Atlassian integration | Blocks raw Confluence data from being written into Jira | `python -m demos.integrations.atlassian.demo` |
| Dashboard/API | Generates mixed audit decisions and verifies dashboard endpoints | `python -m demos.product.dashboard.demo` |
| Web launcher | Starts FastAPI and opens the dashboard | `python -m demos.product.dashboard.web_launcher` |
| ZombieAgent narrative | Three-act taint/exfiltration story with world switch to lockdown | `bash demos/narratives/zombieagent/run.sh` |
| Safe Skills Projection | Compares unsafe skill discovery with projected safe capabilities | `python -m demos.safe_skills.run_with_proxy` |
| MCPZero | Runs attack corpus in baseline and protected modes | `python -m mcpzero.demo` or `python -m demos.mcpzero.demo` |

## Layout

| Path | Purpose |
|---|---|
| `core/` | Minimal deterministic policy demos. |
| `integrations/` | Runtime-specific demos for Claude Code, Gemini, and Atlassian MCP. |
| `product/dashboard/` | Dashboard smoke demo and one-click web launcher. |
| `narratives/zombieagent/` | Rich terminal narrative with support-ticket data and optional MCP upstream server. |
| `safe_skills/` | Skills supply-chain and capability projection demo. |
| `mcpzero/` | MCPZero launcher wrapper and notebook assets. |
| `assets/` | Demo GIF tapes and generated visual assets. |

## Shared Inputs

`attacks/` remains at the repository root. It is not a runnable demo; it is the
structured attack corpus used by MCPZero, tests, and scenario APIs.

`worlds/`, `safe_mcp_proxy/config/worlds/`, and `manifests/` remain with the
runtime code because they are policy inputs used outside demos too.
