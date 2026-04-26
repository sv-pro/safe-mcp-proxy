# `mcpzero/generator/attack_gen.py`

## Role

Generates `tool_chain`-type attack scenarios programmatically by reading the
tool surface inventory (`tools/tool_graph.yaml`) and building read→external
chains for each tool with `side_effect_type: external`.

## Key symbols

| Name | Kind | Description |
|------|------|-------------|
| `generate(tool_graph_path)` | function | Returns a list of raw scenario dicts (not `AttackScenario` instances) |
| `_load_tool_graph(path)` | function | Parses `tool_graph.yaml` and returns the `tools` list |
| `TOOL_GRAPH` | `Path` | Default path: `mcpzero/tools/tool_graph.yaml` |

## Generation strategy

For each tool where `side_effect_type == "external"`:

1. Extract `required` fields from the tool schema
2. Build a placeholder payload `{field: "<field>"}` for each required field
3. Emit a two-step scenario: `read_file → <external_tool>`, `source_channel: web`
4. Set `expected.baseline: ALLOW`, `expected.protected: DENY`

## Output format

Each generated scenario is a plain `dict` conforming to the `attacks/schema.yaml`
structure. It can be written to a YAML file and loaded via `attacks/loader.load()`.

## Depends on

- `yaml` (PyYAML) — tool graph parsing
- `mcpzero/tools/tool_graph.yaml` — tool surface data

## Used by

- `tests/test_mcpzero.py` — `TestAttackGenerator`
- Future: CI pipeline to auto-generate regression scenarios

## See also

- [[src/mcpzero/index]] — package overview
- [[src/attacks/loader]] — format the generated dicts conform to
