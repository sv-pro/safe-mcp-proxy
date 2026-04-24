# `provenance.py`

## Role

Defines the `Provenance` dataclass and taint classification logic. Tracks source channel and propagates taint through tool output chains.

## Key symbols

| Name | Kind | Description |
|------|------|-------------|
| `TAINTED_CHANNELS` | constant | `{"email", "web", "tool_output"}` |
| `Provenance` | frozen dataclass | Carries `source_channel`, `tainted`, `parent_sources` |
| `Provenance.from_source` | classmethod | Factory; sets `tainted` based on channel and parents |
| `Provenance.derive` | method | Creates child provenance; taint is monotonic (never cleared) |

## `from_source()` logic

```python
tainted = source_channel in TAINTED_CHANNELS
         or any(parent in TAINTED_CHANNELS for parent in parent_sources)
```

## `derive()` logic

```python
tainted = self.tainted or source_channel in TAINTED_CHANNELS
parent_sources = self.parent_sources + (self.source_channel,)
```

Once tainted, `tainted` is never set back to `False` regardless of subsequent source channels.

## Used by

- [[src/safe_mcp_proxy/executor]] — `provenance.tainted` passed to `policy_engine.decide()`
- [[src/safe_mcp_proxy/main]] — `Provenance.from_source(args.source)`
- [[src/api/index]] — `Provenance.from_source(scenario.source_channel)`
- [[src/safe_mcp_proxy/scenarios/index]] — `scenarios.run()` creates provenance per scenario

## See also

- [[provenance-taint]] — concept page with threat model
- [[absent-deny]] — taint leads directly to DENY rule 4
- [[policy-engine]] — `taint` is the fourth input to `decide()`
- [[architecture]] — Provenance is stage 1 (classification) in the fixed pipeline
