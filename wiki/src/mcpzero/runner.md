# `mcpzero/runner/interface.py`

## Role

Scenario execution interface for the MCPZero Demo. Loads attack scenarios from
the corpus and dispatches them to either `BaselineAgent` (no policy) or
`SafeMCPProxy` (full enforcement) based on the configured mode. Optionally
records every step to an `ExecutionObserver`.

## Key symbols

| Name | Kind | Description |
|------|------|-------------|
| `MODES` | tuple | `("baseline", "protected")` — valid mode values |
| `RunResult` | dataclass | `mode`, `scenario_name`, `steps: List[dict]` |
| `RunResult.last_decision` | property | Decision of the final step |
| `RunResult.decisions` | method | List of all step decisions |
| `ScenarioRunner` | class | Dispatches a scenario to the right agent based on mode |
| `ScenarioRunner.__init__` | method | Accepts `mode: str`; raises `ValueError` for unknown modes |
| `ScenarioRunner.run` | method | Runs scenario, optionally records to observer, returns `RunResult` |
| `load_scenario` | function | Load by name (searches `attacks/`) or by explicit file path |
| `load_all_scenarios` | function | Load every scenario in the attacks corpus |

## Mode switch (I7)

`ScenarioRunner(mode="baseline")` — calls `BaselineAgent().run(scenario)`  
`ScenarioRunner(mode="protected")` — calls `SafeMCPProxy().run(scenario)`

The two modes share identical inputs (same scenario, same steps) and produce
structurally identical output dicts. Only the `decision` and `rule` values differ.

## Observer wiring

If `observer` is passed to `run()`, each step result is forwarded to
`observer.record(...)` after execution. The runner does not instantiate the
observer; the caller creates and owns it.

## Depends on

- [[src/attacks/loader]] — `AttackScenario`, `load`, `load_all`
- [[src/mcpzero/agent]] — `BaselineAgent` (baseline mode)
- [[src/mcpzero/proxy]] — `SafeMCPProxy` (protected mode)
- [[src/mcpzero/observer]] — `ExecutionObserver` (optional)

## Used by

- [[src/mcpzero/index]] — `mcpzero/demo.py` creates two runners per scenario
- `tests/test_mcpzero.py` — `TestScenarioRunner`

## See also

- [[src/mcpzero/index]] — data flow diagram
- [[provenance-taint]] — the taint rules that make baseline and protected differ
