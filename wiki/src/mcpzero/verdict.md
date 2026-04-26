# `mcpzero/verdict/engine.py` and `mcpzero/metrics/reporter.py`

## Role

Compare baseline and protected run results step-by-step to determine whether
the demo's "attack succeeds / proxy blocks" contract holds. Produce structured
JSON output consumed by CI and the CLI summary.

## Key symbols — verdict engine

| Name | Kind | Description |
|------|------|-------------|
| `StepVerdict` | dataclass | Per-step comparison: `tool`, `baseline_decision`, `protected_decision` |
| `StepVerdict.succeeded_baseline` | property | `baseline_decision == "ALLOW"` |
| `StepVerdict.blocked_protected` | property | `protected_decision in {"DENY", "ABSENT"}` |
| `Verdict` | dataclass | Aggregated result for one scenario: `scenario`, `steps` |
| `Verdict.attack_succeeded` | property | Any step returned ALLOW in baseline |
| `Verdict.proxy_blocked` | property | Proxy blocked at least one baseline-allowed step |
| `Verdict.demo_pass` | property | `attack_succeeded AND proxy_blocked` |
| `Verdict.to_dict` | method | Serialises to JSON-friendly dict |
| `compare` | function | Aligns baseline and protected `RunResult` steps → `Verdict` |
| `save` | function | Writes `[Verdict.to_dict(), …]` to a JSON file |

## `proxy_blocked` semantics

`True` when **at least one** step that was ALLOW in baseline is DENY/ABSENT in
protected. Safe steps (e.g. `read_file`) remain allowed in protected mode —
this is correct and expected. Only the dangerous step(s) (e.g. `send_email`)
need to be blocked for the demo to pass.

## Key symbols — metrics reporter

| Name | Kind | Description |
|------|------|-------------|
| `compute_asr` | function | Fraction of scenarios where `attack_succeeded` |
| `compute_block_rate` | function | Among attacked scenarios, fraction where `proxy_blocked` |
| `to_dict` | function | `{total, asr, block_rate, demo_pass}` summary dict |
| `save` | function | Writes metrics dict to JSON |
| `print_summary` | function | Prints human-readable summary to stdout |

## Depends on

- [[src/mcpzero/index]] — `RunResult` from runner/interface
- [[src/attacks/loader]] — `AttackScenario`

## See also

- [[src/mcpzero/index]] — overall demo pipeline
- [[absent-deny]] — DENY / ABSENT outcomes that constitute `blocked_protected`
