# `attacks/loader.py`

## Role

Parses, validates, and exposes YAML and JSON attack scenarios as typed Python
dataclasses. Also reads raw Markdown document files referenced by scenarios.

## Key symbols

| Name | Kind | Description |
|------|------|-------------|
| `AttackStep` | dataclass | `tool: str`, `payload: Dict[str, Any]` — one invocation in an attack chain |
| `AttackScenario` | dataclass | Full scenario: name, description, type, source_channel, steps, expected decisions, optional document text, optional poison_tool |
| `load(path)` | function | Parse and validate a single YAML or JSON scenario file; returns `AttackScenario` |
| `load_document(path)` | function | Read a raw `.md` file and return its text content |
| `load_all(directory)` | function | Load all `.yaml` and `.json` files in a directory, skipping `schema.yaml`; returns list of `AttackScenario` |
| `ATTACKS_DIR` | `Path` | Absolute path to the `attacks/` package directory |
| `VALID_TYPES` | set | `{"email_injection", "tool_chain", "mcp_poison"}` |
| `VALID_CHANNELS` | set | `{"cli", "email", "web", "tool_output"}` |
| `VALID_DECISIONS` | set | `{"ALLOW", "DENY", "ABSENT"}` |

## `AttackScenario` fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | str | Unique snake_case identifier |
| `description` | str | Human-readable summary |
| `type` | str | One of `VALID_TYPES` |
| `source_channel` | str | One of `VALID_CHANNELS`; fed to `Provenance.from_source()` |
| `steps` | list[AttackStep] | Ordered tool invocations the attack relies on |
| `expected_baseline` | str | Predicted decision without proxy (`ALLOW`/`DENY`/`ABSENT`) |
| `expected_protected` | str | Predicted decision with proxy (`ALLOW`/`DENY`/`ABSENT`) |
| `document` | str | Raw text of the companion `.md` file, or `""` if not set |
| `poison_tool` | dict \| None | For `mcp_poison` type: `{name, tampered_schema}` applied by `SafeMCPProxy._apply_poison()` |

## Validation

`_parse()` enforces:
- All required fields present
- `type` in `VALID_TYPES`
- `source_channel` in `VALID_CHANNELS`
- Both `expected.baseline` and `expected.protected` in `VALID_DECISIONS`

Raises `ValueError` with the file path and field name on any violation.

## Document inlining

If a YAML scenario declares a `document` field (e.g. `document: email_injection.md`),
`load()` resolves the path relative to the scenario file's directory and calls
`load_document()` to inline the raw text into `AttackScenario.document`.

## JSON support

`load()` detects `.json` suffix and uses `json.load()` instead of `yaml.safe_load()`.
`load_all()` collects both `*.yaml` and `*.json` files (sorted alphabetically within
each glob). The schema and validation rules are identical for both formats.

## Depends on

- `yaml` (PyYAML) — YAML parsing
- `json` (stdlib) — JSON parsing

## Used by

- `attacks/__init__.py` — re-exports public API
- `tests/test_attack_corpus.py` — load, validation, and field tests
- [[src/mcpzero/runner]] — `load_scenario()` and `load_all_scenarios()`
- [[src/mcpzero/proxy]] — `AttackScenario` consumed by `SafeMCPProxy.run()`

## See also

- [[src/attacks/index]] — package overview and scenario catalogue
- [[provenance-taint]] — `source_channel` values match `Provenance.from_source()` inputs
- [[descriptor-drift]] — `mcp_poison` scenarios exploit this mechanism
