# `mcpzero/`

## Role

Self-contained MCPZero Demo package (EPIC 11). Runs an attack scenario in two
modes — baseline (direct tool access, attack succeeds) and protected (routed
through Safe MCP Proxy, attack blocked deterministically) — and produces a
side-by-side comparison with JSON traces, verdicts, and metrics.

## Entry point

```
python -m mcpzero.demo                          # run all scenarios
python -m mcpzero.demo --scenario email_injection
python -m mcpzero.demo --output results/
```

## Layout

| Module / directory | Description |
|--------------------|-------------|
| `demo.py` | CLI entry point — runs all scenarios in both modes, prints comparison |
| `agent/runner.py` | [[src/mcpzero/agent]] — `BaselineAgent`, direct tool execution, no policy |
| `runner/interface.py` | [[src/mcpzero/runner]] — `ScenarioRunner`, mode switch, observer wiring |
| `proxy/proxy.py` | [[src/mcpzero/proxy]] — `SafeMCPProxy`, wraps executor with mcpzero_demo world |
| `tools/tool_graph.yaml` | Static tool surface inventory: schemas, `side_effect_type` |
| `generator/attack_gen.py` | [[src/mcpzero/generator]] — generates read→external chains from tool graph |
| `observer/observer.py` | [[src/mcpzero/observer]] — `ExecutionObserver`, JSONL traces to `mcpzero/traces/` |
| `verdict/engine.py` | [[src/mcpzero/verdict]] — `Verdict`, `compare()`, `save()` |
| `metrics/reporter.py` | [[src/mcpzero/verdict]] — ASR, block_rate, `print_summary()`, `save()` |
| `traces/` | Runtime trace files (gitignored; `.gitkeep` holds the directory) |

## World manifest

`worlds/mcpzero_demo.yaml` — dedicated world for the demo. `send_email` is in
the allowlist but carries no approval gate; the taint rule (`tainted_external: deny`)
blocks it whenever the source channel is `web`, `email`, or `tool_output`.

## Data flow

```
attacks/            →  ScenarioRunner
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
        BaselineAgent           SafeMCPProxy
        (no policy)           (safe_mcp_proxy)
              │                         │
              └────────┬────────────────┘
                       ▼
                 ExecutionObserver  →  traces/*.jsonl
                       ▼
                  VerdictEngine    →  verdict.json
                       ▼
                  MetricsReporter  →  metrics.json
```

## See also

- [[src/attacks/index]] — attack corpus loaded by the runner
- [[src/mcpzero/agent]] — BaselineAgent detail
- [[src/mcpzero/runner]] — ScenarioRunner and mode switch
- [[src/mcpzero/proxy]] — SafeMCPProxy detail
- [[src/mcpzero/generator]] — attack scenario generator
- [[src/mcpzero/observer]] — trace logger
- [[src/mcpzero/verdict]] — verdict and metrics detail
- [[provenance-taint]] — taint mechanism the proxy enforces
- [[absent-deny]] — DENY vs ABSENT outcomes shown in demo output
