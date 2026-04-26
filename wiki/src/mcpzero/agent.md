# `mcpzero/agent/runner.py`

## Role

Baseline agent for the MCPZero Demo. Executes scenario steps directly against
mock tool handlers — no registry filtering, no policy engine, no taint checks.
Every known tool returns ALLOW; this is the "attack succeeds" control group.

## Key symbols

| Name | Kind | Description |
|------|------|-------------|
| `BaselineAgent` | class | Simulated agent with direct tool access |
| `BaselineAgent.__init__` | method | Accepts optional `handlers` dict; defaults to `_DEFAULT_HANDLERS` |
| `BaselineAgent.run` | method | Executes all steps in an `AttackScenario`; returns list of step result dicts |
| `_DEFAULT_HANDLERS` | dict | Mock handlers for `read_file`, `list_repo`, `send_email`, `dangerous_exec` |

## Step result dict

```python
{
    "tool":     str,
    "payload":  dict,
    "decision": "ALLOW" | "ABSENT",   # ALLOW if handler found, ABSENT if unknown
    "rule":     "no_policy" | "tool_unknown",
    "result":   dict | None,
}
```

## Behaviour

- Known tools: handler is called directly with the step payload → `decision: ALLOW`
- Unknown tools: no handler found → `decision: ABSENT, rule: tool_unknown`
- No source channel or taint evaluation is performed

## Depends on

- [[src/attacks/loader]] — `AttackScenario`

## Used by

- [[src/mcpzero/runner]] — `ScenarioRunner(mode="baseline")`

## See also

- [[src/mcpzero/proxy]] — the protected counterpart that enforces policy
- [[src/mcpzero/index]] — overall demo pipeline
