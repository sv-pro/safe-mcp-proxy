# The World Manifest: Your Agent's Reality Is a YAML File

Every safe-mcp-proxy deployment starts with a declaration: *what exists in this world?*

That declaration is `world_manifest.yaml`. It is the single authoritative policy surface.
Every tool invocation, every capability decision, every taint rule — all of it flows from
this file, compiled once at startup into an immutable runtime config.

---

## What a world is

A "world" is the complete set of tools and capabilities visible to an agent in a given
context. The world manifest defines the world.

```yaml
world_id: "repo_assistant"

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
    requires_approval: true

taint_rules:
  - tainted_external: deny

side_effects:
  external: restricted
```

In this world, the agent can see `read_file`, `list_repo`, and `send_email`. It cannot
see anything else — not because those tools are blocked, but because they do not exist
here. An agent running in a `read_only` world that declares only `read_file` has no
concept of `send_email`.

---

## Compiled once, never mutated

The manifest is loaded by `compile_world_manifest()` in `compiler.py` at startup. The
result is a typed dict with these keys:

| Key | Source field | Used by |
|-----|-------------|---------|
| `allowlist` | `allowed_tools` | Registry filter; ABSENT rule 1 |
| `capability_map` | `capabilities[*].allowed` | ABSENT rule 2 |
| `approval_required` | `capabilities[*].requires_approval` | ASK rule 5 |
| `taint_rules` | `taint_rules` | Passed to policy engine |
| `side_effect_policy` | `side_effects` | Passed to policy engine |
| `capability_definitions` | `capability_definitions` | Registry scoped tool builder |

Once compiled, the config is never reloaded. Runtime manifest changes have no effect
until the process restarts. This is not a limitation — it is a deliberate design
choice that enables deterministic forensics: every audit log entry is anchored to
an exact policy snapshot.

---

## Parameterized capabilities

The optional `capability_definitions` section lets you define constrained forms of
base tools. The classic example is scoped email:

```yaml
capability_definitions:
  send_me_email:
    base_tool: send_email
    args:
      to:
        valueFrom:
          literal:
            value: "owner@example.com"   # locked — actor cannot override
      body:
        valueFrom:
          actor_input: {}                # free — actor supplies at call time
```

`send_me_email` is a projection of `send_email` where the `to` field is locked to a
literal value. The actor can supply the message body but cannot redirect the recipient.
Even a successful prompt injection that reaches this tool cannot send email to an
arbitrary address.

The locked argument is injected *after* payload stripping — the actor's payload is
filtered to expose only `actor_input` fields, then the literals are merged in. The
actor never sees the locked values and cannot override them.

---

## Multiple worlds

The same agent code can operate in different worlds. Named world files are searched in:
1. `safe_mcp_proxy/config/worlds/<world_id>.yaml`
2. `worlds/<world_id>.yaml`

Built-in worlds in this repo:
- `world_a` — full access (`read_file`, `list_repo`, `send_email`)
- `world_b` — read-only (`read_file` only)
- `world_c` — no email (`read_file`, `list_repo`)
- `read_only` — `read_file` only

The `/compare` API endpoint runs the same tool invocation across multiple worlds
simultaneously — useful for auditing what different agents are permitted to do.

```bash
python -m safe_mcp_proxy.main --tool send_email --source web --world world_b \
  --payload '{"to": "test@example.com", "body": "hello"}'
# → ABSENT: send_email does not exist in world_b
```

---

## Why a single YAML file

Several alternatives were considered: code-defined policies, database-backed rules,
dynamic reloading. The YAML manifest was chosen because:

1. **Operator-readable** — the entire policy surface fits on one screen. An operator
   can audit it without reading Python.

2. **Version-controlled** — `world_manifest.yaml` is committed to the repo. Every
   policy change has a git diff, a commit message, and a timestamp.

3. **Forensically stable** — because the manifest is compiled once and never reloaded,
   every audit entry maps to an exact policy state. The SHA256 of the manifest file
   is the policy version; it appears in every trace log entry.

4. **Declarative, not imperative** — the manifest describes *what exists*, not *how
   to decide*. The decision logic lives in `policy_engine.py`. Keeping them separate
   makes both easier to audit.

---

## See also

- [Repository](https://github.com/sv-pro/safe-mcp-proxy)
- `world_manifest.yaml` — the live manifest in this repo
- `safe_mcp_proxy/compiler.py` — parses the manifest
- `worlds/` — named world variants
- `wiki/world-manifest.md` — concept page
- `wiki/absent-deny.md` — how the allowlist produces ABSENT
