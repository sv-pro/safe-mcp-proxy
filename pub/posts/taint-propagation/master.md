# Taint Propagation: Data Origin Is Execution Context

The classic prompt injection scenario: an agent reads a web page. The page contains
a hidden instruction. The agent follows it and calls `send_email`, exfiltrating
everything in its context window to an attacker's address.

The attack works not because the model is misaligned, but because the agent treats
data from the web — an untrusted source — as equivalent to instructions from a trusted
operator.

Taint propagation is the mechanism that prevents this.

---

## What taint is

Every request to the policy engine carries a `Provenance` object — a frozen dataclass
that records where the data came from:

```python
@dataclass(frozen=True)
class Provenance:
    source_channel: str           # "cli", "email", "web", "tool_output"
    tainted: bool                 # True if channel is untrusted
    parent_sources: tuple[str, ...] # lineage chain for audit
```

Tainted channels are declared statically:

```python
TAINTED_CHANNELS = {"email", "web", "tool_output"}
```

Any request arriving from `email`, `web`, or `tool_output` is automatically tainted.
`cli` is the only clean channel.

---

## How taint propagates

Taint is **monotonic** — once set, it is never cleared.

**From source:**
```python
Provenance.from_source("web")
# → tainted = True (web is in TAINTED_CHANNELS)
```

**Through derivation:**
```python
web_provenance.derive("tool_output")
# → tainted = True (was already tainted; monotonic)
# → parent_sources = ("web",)
```

A chain of tool calls that starts with a web-sourced input remains tainted for its
entire lifetime. Even if an intermediate step goes through a "clean" channel, the taint
is preserved:

```
web request → tainted=True
  ↓ (tool output feeds into next request)
tool_output → still tainted=True (derive propagates)
  ↓ (attempts send_email with external side effect)
DENY / tainted_external_side_effect
```

---

## The policy rule

Rule 4 in the policy engine:

```
taint == True AND side_effect_type == "external"
  → DENY / tainted_external_side_effect
```

This blocks the exfiltration path. An agent reading a web page (tainted) cannot be
directed to call `send_email` (external side effect). Even if the model decides the
instruction is valid, the policy engine blocks the call before execution.

Read operations are not blocked. `read_file` from a tainted source is allowed — an
agent can read files regardless of where its input came from. Only *external* side
effects — actions that send data outside the system — are blocked when tainted.

---

## Running the demo

```bash
python -m demos.core.prompt_injection
```

This invokes `send_email` with `source="web"` — simulating an agent that read a web
page containing an injection instruction. The policy engine evaluates:

1. `send_email` is in the allowlist — not ABSENT
2. capability is enabled — not ABSENT
3. schema hash is valid — not descriptor_drift
4. `tainted=True` AND `side_effect_type="external"` → **DENY / tainted_external_side_effect**

The audit log records the decision with `taint: true` and `source_channel: "web"`.

---

## What monotonicity buys

Non-monotonic taint would allow an attacker to "launder" tainted data through an
intermediate clean channel and then call an external tool. Monotonicity closes this:
once a request chain starts from an untrusted source, no subsequent step can make it
trusted again.

This is conservative — there will be legitimate workflows where taint blocks an
operation that would have been safe. The trade-off is deliberate: fewer false negatives
(missed attacks) matters more than fewer false positives (blocked legitimate operations)
in this threat model.

---

## The attack scenario

The attack corpus at `attacks/email_injection.yaml` formalizes this scenario:
an email with a hidden injection instruction directs the agent to call `send_email`
with the email body as the payload. With safe-mcp-proxy in the path, the request is
denied at rule 4. Without it, the call executes.

---

## See also

- [Repository](https://github.com/sv-pro/safe-mcp-proxy)
- `safe_mcp_proxy/provenance.py` — implementation
- `demos/core/prompt_injection.py` — demo
- `attacks/email_injection.yaml` — formalized attack scenario
- `wiki/provenance-taint.md` — concept page
