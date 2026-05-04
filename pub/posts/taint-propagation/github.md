# Taint Propagation: Data Origin Is Execution Context

Prompt injection works because agents treat untrusted data as trusted instructions. [safe-mcp-proxy](https://github.com/sv-pro/safe-mcp-proxy) tracks data origin and blocks external side effects when the origin is untrusted.

## How it works

Every request carries a `Provenance` (frozen dataclass):

```python
TAINTED_CHANNELS = {"email", "web", "tool_output"}

provenance = Provenance.from_source("web")
# → tainted = True
```

Taint is **monotonic** — propagates through derivation, never cleared:

```python
web_provenance.derive("tool_output")
# → still tainted (parent_sources = ("web",))
```

## The policy rule

```
taint == True AND side_effect_type == "external"
  → DENY / tainted_external_side_effect
```

Read operations (`read_file`) are allowed from tainted sources. External side effects (`send_email`) are not.

## Demo

```bash
python -m demos.core.prompt_injection
# → DENY / tainted_external_side_effect
```

The audit log entry: `{"taint": true, "source_channel": "web", "decision": "DENY", "rule": "tainted_external_side_effect"}`

**See also:** [`wiki/provenance-taint.md`](../../wiki/provenance-taint.md) · [`attacks/email_injection.yaml`](../../attacks/email_injection.yaml)
