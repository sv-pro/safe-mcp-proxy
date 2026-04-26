# Project Root

Top-level files and directories in the safe-mcp-proxy repository.

## Entry points

| File | Description |
|------|-------------|
| `world_manifest.yaml` | Default world definition — the primary policy surface. See [[world-manifest]]. |
| `demo.py` | Standalone demo script |
| `run_demo.py` | One-click demo launcher (starts API + UI) |

## Packages

| Directory | Description |
|-----------|-------------|
| [[src/safe_mcp_proxy/index]] | Core enforcement package — all policy logic lives here |
| [[src/api/index]] | FastAPI HTTP layer |
| [[src/tests/index]] | Test suite |
| [[src/attacks/index]] | Attack corpus for MCPZero Demo — YAML/MD scenarios and loader |

## Configuration directories

| Directory | Description |
|-----------|-------------|
| `worlds/` | Legacy world YAML files (`repo_assistant.yaml`, `read_only.yaml`, `world_a/b/c.yaml`) |
| `seeds/` | `demo.jsonl` — pre-generated traces for seeding an empty UI |
| `pub/posts/` | Blog posts about the project (multi-platform markdown) |
| `ui/` | `index.html` — single-page frontend for the demo UI |

## See also

- [[world-manifest]] — world_manifest.yaml explained
- [[architecture]] — full pipeline overview
- [[absent-deny]] — the core semantic distinction enforced by this project
- [[audit-replay]] — `safe_mcp_proxy/logs/audit.jsonl` lives in this repo
