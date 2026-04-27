# The World Manifest: Your Agent's Reality Is a YAML File

Every [safe-mcp-proxy](https://github.com/sv-pro/safe-mcp-proxy) deployment starts with `world_manifest.yaml` — the single authoritative policy surface. Compiled once at startup. Never mutated at runtime.

## What it declares

```yaml
world_id: "repo_assistant"

allowed_tools:
  - read_file
  - list_repo
  - send_email      # visible but requires approval

capabilities:
  send_email:
    allowed: true
    requires_approval: true

taint_rules:
  - tainted_external: deny
```

Tools not in `allowed_tools` are **ABSENT** — not "not found," absent. They don't exist in this world.

## Compiled into immutable config

`compile_world_manifest()` in `compiler.py` produces:

| Key | Used by |
|-----|---------|
| `allowlist` | Registry filter — ABSENT rule 1 |
| `capability_map` | ABSENT rule 2 |
| `approval_required` | ASK rule 5 |

Once compiled, the config is never reloaded. Every audit log entry is anchored to this exact policy state.

## Parameterized capabilities

Lock individual args while keeping others free:

```yaml
capability_definitions:
  send_me_email:
    base_tool: send_email
    args:
      to:
        valueFrom:
          literal: {value: "owner@example.com"}  # locked
      body:
        valueFrom:
          actor_input: {}                          # free
```

Even a successful injection can't redirect the `to` field — it's injected after payload stripping.

## Multiple worlds

```bash
# send_email is ABSENT in world_b (read-only)
python -m safe_mcp_proxy.main --tool send_email --source web --world world_b \
  --payload '{"to":"test@example.com","body":"hello"}'
```

**See also:** [`wiki/world-manifest.md`](../../wiki/world-manifest.md) · [`compiler.py`](../../safe_mcp_proxy/compiler.py)
