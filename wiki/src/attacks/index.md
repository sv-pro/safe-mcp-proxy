# `attacks/`

## Role

Attack corpus for the MCPZero Demo (EPIC 11). Contains structured attack scenario
configs (YAML), raw adversarial documents (Markdown), and the Python loader that
parses and validates them.

## Layout

| File | Description |
|------|-------------|
| `schema.yaml` | Canonical field definitions for structured YAML/JSON scenarios |
| `example.yaml` | Minimal working scenario (`example_exfil`) — used in tests |
| `email_injection.md` | Adversarial business document with a hidden prompt injection instruction |
| `email_injection.yaml` | Scenario config: web channel, read_file → send_email chain |
| `tool_chain.yaml` | Multi-step taint chain: tool_output channel, list_repo → read_file → send_email |
| `mcp_poison.json` | JSON scenario: tampered read_file descriptor triggers descriptor drift |
| `loader.py` | Parses and validates YAML and JSON attack scenarios as Python dataclasses |
| `__init__.py` | Re-exports the public loader API |

## Scenario formats

Two formats coexist:

- **YAML/JSON** — structured scenarios declaring `type`, `source_channel`, `steps`,
  and `expected` outcomes. Loaded and validated by `loader.py`.
- **Markdown** — raw adversarial documents fed verbatim to the agent as content.
  Referenced by a companion YAML via the `document` field; inlined at load time.

## See also

- [[src/attacks/loader]] — detailed symbol reference for the loader
- [[provenance-taint]] — `source_channel` maps directly to taint classification
- [[absent-deny]] — `expected.protected` values mirror ABSENT/DENY decisions
- [[src/safe_mcp_proxy/scenarios/index]] — the existing Python-native scenario registry
