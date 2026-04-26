# `mcpzero/observer/observer.py`

## Role

Append-only trace logger for MCPZero Demo runs. Records every tool call and
policy decision to a JSONL file under `mcpzero/traces/`. One `ExecutionObserver`
instance covers both the baseline and protected passes of a run so the full
side-by-side trace lives in a single file.

## Key symbols

| Name | Kind | Description |
|------|------|-------------|
| `ExecutionObserver` | class | Per-run trace logger |
| `ExecutionObserver.__init__` | method | Creates `traces/run_<timestamp>Z.jsonl`; `trace_dir` defaults to `mcpzero/traces/` |
| `ExecutionObserver.record` | method | Appends one entry to the in-memory list and the JSONL file |
| `ExecutionObserver.entries` | property | Returns a copy of all recorded entries |
| `ExecutionObserver.log_path` | property | `Path` to the current trace file |
| `TRACES_DIR` | `Path` | `mcpzero/traces/` (gitignored at runtime, held by `.gitkeep`) |

## Trace entry schema

```json
{
  "timestamp": "<ISO-8601 UTC>",
  "mode":      "baseline" | "protected",
  "scenario":  "<scenario_name>",
  "tool":      "<tool_name>",
  "payload":   {},
  "decision":  "ALLOW" | "DENY" | "ABSENT",
  "rule":      "<rule_name>",   // omitted if null
  "result":    {}               // omitted if null
}
```

## Wiring

`ExecutionObserver` is passed as an optional argument to `ScenarioRunner.run()`.
The runner calls `observer.record(...)` for each step after execution. The demo
(`mcpzero/demo.py`) creates one observer per full demo run and prints its
`log_path` in the summary footer.

## Depends on

- `json`, `datetime` (stdlib)

## Used by

- [[src/mcpzero/runner]] — `ScenarioRunner.run(observer=...)`
- [[src/mcpzero/index]] — `demo.py` creates one observer per run

## See also

- [[audit-replay]] — the main proxy audit log (`safe_mcp_proxy/logs/audit.jsonl`) uses the same JSONL pattern
- [[src/mcpzero/index]] — data flow diagram
