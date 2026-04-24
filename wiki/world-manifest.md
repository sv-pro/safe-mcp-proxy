# World Manifest

The primary policy surface. A YAML file that defines a "world" — the complete set of tools, capabilities, taint rules, and side-effect policies visible to an agent in this context.

## What it is

`world_manifest.yaml` (repo root) is the static world definition. It is the single authoritative source for what is allowed and what does not exist.

```yaml
world_id: "repo_assistant"

policy_engine: python   # "python" (default) or "opa"

allowed_tools:
  - read_file
  - list_repo
  - send_email

capabilities:
  read_file:
    allowed: true
  list_repo:
    allowed: true
  send_email:
    allowed: true
  dangerous_exec:
    allowed: false

taint_rules:
  - tainted_external: deny

side_effects:
  external: restricted
```

## Why it exists

Every tool invocation passes through the manifest. The manifest is compiled once at startup into an immutable runtime config — it is never mutated during execution. This gives operators a single declaration point to control the entire tool surface.

Different agents (or the same agent in different contexts) can be given different worlds. A world with only `read_file` makes `send_email` absent — not denied, absent.

## How it works

The manifest is loaded and compiled by [[src/safe_mcp_proxy/compiler]] via `compile_world_manifest()`. The result is a dict with these keys:

| Key | Type | Source field |
|-----|------|-------------|
| `world_id` | `str` | `world_id` |
| `allowlist` | `list[str]` | `allowed_tools` |
| `capability_map` | `dict[str, bool]` | `capabilities[*].allowed` |
| `taint_rules` | `list` | `taint_rules` |
| `side_effect_policy` | `dict` | `side_effects` |
| `policy_engine` | `str` | `policy_engine` |

`build_executor()` in [[src/safe_mcp_proxy/main]] passes `allowlist` and `capability_map` to both the [[src/safe_mcp_proxy/registry]] (for tool filtering) and the [[src/safe_mcp_proxy/policy_engine]] (for decisions).

## Multiple worlds

Named worlds can be stored in two locations (searched in order):
1. `safe_mcp_proxy/config/worlds/<world_id>.yaml`
2. `worlds/<world_id>.yaml`

The CLI `--world` flag selects the world. The API `/compare` endpoint runs the same scenario across multiple worlds simultaneously.

Built-in worlds:
- `world_a` — full access (read_file, list_repo, send_email)
- `world_b` — read-only (read_file only)
- `world_c` — no send_email
- `repo_assistant` — full access
- `read_only` — read_file only

## See also

- [[absent-deny]] — allowlist determines ABSENT
- [[src/safe_mcp_proxy/compiler]] — parses this file
- [[src/safe_mcp_proxy/main]] — loads and wires the manifest
- [[src/safe_mcp_proxy/config/index]] — world file locations
- [[src/safe_mcp_proxy/executor]] — receives compiled manifest tables at construction
- [[src/safe_mcp_proxy/opa_engine]] — receives `allowlist` and `capability_map` from manifest
