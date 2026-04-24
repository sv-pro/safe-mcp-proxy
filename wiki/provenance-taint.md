# Provenance & Taint

Tracks the origin of a request and propagates distrust through tool output chains. Tainted provenance triggers DENY when an external side-effect tool is invoked.

## What it is

`Provenance` is a frozen dataclass that carries three fields:

| Field | Type | Meaning |
|-------|------|---------|
| `source_channel` | `str` | The channel this request arrived on |
| `tainted` | `bool` | True if this or any parent source is untrusted |
| `parent_sources` | `tuple[str, ...]` | Chain of ancestor source channels |

## Tainted channels

```python
TAINTED_CHANNELS = {"email", "web", "tool_output"}
```

Any request arriving from `email`, `web`, or `tool_output` is automatically tainted. `cli` is the only clean channel.

The threat model: an attacker can embed instructions in email content or web pages that an agent reads. If those instructions direct the agent to call a tool with external side effects (like `send_email`), taint propagation ensures the attempt is DENY'd.

## How taint propagates

**From source** (`Provenance.from_source(channel)`):
```python
tainted = channel in TAINTED_CHANNELS
         or any(parent in TAINTED_CHANNELS for parent in parent_sources)
```

**Through derivation** (`provenance.derive(new_channel)`):
```python
# Once tainted, always tainted — even if the next channel is "cli"
tainted = self.tainted or new_channel in TAINTED_CHANNELS
parent_sources = self.parent_sources + (self.source_channel,)
```

Taint is monotonic: it can only be set, never cleared. A chain of tool calls that starts with a web-sourced input remains tainted for its entire lifetime.

## Example

```
Request from "web" → tainted=True
  Tool output feeds into next request → derive("tool_output") → still tainted=True
    That request tries to call send_email (external) → DENY / tainted_external_side_effect
```

## See also

- [[absent-deny]] — taint is the condition for DENY rule 4
- [[policy-engine]] — consumes `provenance.tainted` as the `taint` input
- [[src/safe_mcp_proxy/provenance]] — implementation
