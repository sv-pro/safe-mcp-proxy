# Project Root

Top-level files and directories in the safe-mcp-proxy repository.

## Entry points

| File | Description |
|------|-------------|
| `world_manifest.yaml` | Default world definition — the primary policy surface. See [[world-manifest]]. |
| `demo.py` | Compatibility wrapper for `demos/core/demo_all.py` |
| `run_demo.py` | Compatibility wrapper for `demos/product/dashboard/web_launcher.py` |

## Packages

| Directory | Description |
|-----------|-------------|
| [[src/safe_mcp_proxy/index]] | Core enforcement package — all policy logic lives here |
| [[src/api/index]] | FastAPI HTTP layer |
| [[src/tests/index]] | Test suite |
| [[src/attacks/index]] | Attack corpus for MCPZero Demo — YAML/MD scenarios and loader |
| [[src/mcpzero/index]] | MCPZero Demo — baseline/protected runner, proxy, verdict, metrics |
| [[src/demos/index]] | Canonical runnable demo tree and documentation |

## Demo directories

| Directory | Description |
|-----------|-------------|
| [[src/demos/core]] | Minimal policy-path demo scripts |
| [[src/demos/integrations]] | Claude Code, Gemini, and Atlassian integration demos |
| [[src/demos/product]] | Dashboard demo and one-click web launcher |
| [[src/demos/narratives]] | ZombieAgent narrative demo |
| [[src/demos/safe_skills]] | Safe Skills Projection demo |
| [[src/demos/mcpzero]] | MCPZero wrapper and notebooks |
| [[src/demos/assets]] | VHS tapes and demo media assets |

## Configuration directories

| Directory | Description |
|-----------|-------------|
| `worlds/` | Legacy world YAML files (`repo_assistant.yaml`, `read_only.yaml`, `world_a/b/c.yaml`) |
| `seeds/` | `demo.jsonl` — pre-generated traces for seeding an empty UI |
| `pub/posts/` | Blog posts about the project (multi-platform markdown) |
| `ui/` | `index.html` — single-page frontend for the demo UI |
| `demos/` | Runnable demo scripts, narrative assets, notebooks, and media |

## See also

- [[world-manifest]] — world_manifest.yaml explained
- [[architecture]] — full pipeline overview
- [[absent-deny]] — the core semantic distinction enforced by this project
- [[audit-replay]] — `safe_mcp_proxy/logs/audit.jsonl` lives in this repo
