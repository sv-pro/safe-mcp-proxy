# Gemini Integration Guide

> "Gemini builds agents. Agent Hypervisor defines their world."

## Architecture

```
Gemini Agent
    │
    │  functionCall JSON
    ▼
GeminiAdapter          — parse + normalise to ToolCall
    │
    │  ToolCall
    ▼
SessionManifestBinder  — agent_id / session_id → world_id → Executor (cached)
    │
    │  GeminiProxy (world-scoped)
    ▼
IntentMapper           — ToolCall → IntentIR  (IntentIRError → ABSENT)
    │
    │  IntentIR
    ▼
GeminiPolicyGate       — IntentIR + Provenance → ExecutionSpec
    │
    │  ExecutionSpec (decision + rule)
    ▼
Executor               — ALLOW: execute tool
                       — DENY:  log + return denial  (no execution)
                       — ABSENT: log + return absence (no execution)
                       — ASK:  create approval token (INTERACTIVE) or DENY (BACKGROUND)
    │
    │  result dict
    ▼
GeminiAdapter.format_response → functionResponse JSON
    │
    ▼
Gemini Agent
```

## Request Flow (step-by-step)

1. **Adapter normalisation** — `GeminiAdapter.parse()` converts the Gemini
   `functionCall` envelope into a typed `ToolCall`. Raises `GeminiAdapterError`
   for malformed requests.

2. **Session / world binding** — `SessionManifestBinder.bind()` resolves the
   correct `world_id` for the requesting agent using `agent_id` from the request
   metadata. Falls back to the restrictive `read_only` world when no explicit
   mapping exists. Executors are cached per `world_id`.

3. **Intent IR mapping** — `IntentMapper.map()` looks up the tool in the full
   catalog (not just the allowlist). If the tool is unknown to the system,
   `IntentIRError` is raised — this produces an immediate ABSENT response with
   rule `action_not_in_ontology`.

4. **Policy evaluation** — `GeminiPolicyGate.evaluate()` runs the world
   manifest policy against the `IntentIR` and `Provenance`. Returns an
   `ExecutionSpec` with decision and rule.

5. **Execution routing** — `GeminiProxy.execute()` dispatches based on decision:
   | Decision | Action |
   |----------|--------|
   | ALLOW    | Forward `ToolCall` to executor; audit-logged |
   | DENY     | Log via `record_denial()`; return denial; no execution |
   | ABSENT   | Log via `record_absence()`; return absence; no execution |
   | ASK      | Executor creates approval token (INTERACTIVE) or returns DENY (BACKGROUND) |

6. **Provenance & trace** — `GeminiTraceLogger` appends one JSON line per
   pipeline stage to `data/traces/gemini_trace.jsonl`. Stages: `request`,
   `tool_call`, `intent`, `policy`, `execution` (or `absent`). Every entry
   carries `world_id`, `agent_id`, `session_id`, `taint`, and `source_channel`.

## Enforcement Points

| Gate | What it checks |
|------|---------------|
| `GeminiAdapter` | Request shape; required fields present |
| `IntentMapper` | Tool exists anywhere in the system ontology |
| `PolicyEngine` (via gate) | Tool in world allowlist; capability enabled; taint rules; descriptor integrity |
| `Executor` | Final dispatch; approval token lifecycle; audit log |

## Demo Explanation

`safe_mcp_proxy/examples/gemini_demo.py` proves the architectural difference:

```
BASELINE (without Agent Hypervisor):
  send_email → ALLOW
  ATTACK SUCCEEDED

PROTECTED (with Agent Hypervisor / gemini_demo world):
  send_email → ABSENT (tool_not_allowlisted)
  ATTACK IMPOSSIBLE
```

The `gemini_demo` world only exposes `read_logs` and `investigate_incident`.
`send_email` is not in the allowlist — it does not exist in this world.
The block is deterministic and policy-driven, not model-driven.

Run:
```bash
python -m safe_mcp_proxy.examples.gemini_demo
```

## Configuration

### Point Gemini at the proxy

In your Gemini agent configuration, replace direct tool calls with requests
to the Safe MCP Proxy endpoint (via the FastAPI server):

```bash
uvicorn api.main:app --reload
# POST /gemini/execute  with functionCall JSON
```

### Select a world manifest per agent

Use `SessionManifestBinder` to map agent identities to worlds:

```python
from safe_mcp_proxy.integrations.session_binder import SessionManifestBinder
from pathlib import Path

binder = SessionManifestBinder(
    base_dir=Path("/path/to/repo"),
    agent_manifest_map={
        "agent-prod":    "gemini_demo",   # limited tool surface
        "agent-readonly": "read_only",    # read-only world
    },
    default_world_id="read_only",  # restrictive fallback
)
proxy, world_id = binder.bind(tool_call)
result = proxy.execute(request)
```

### World manifest format

See `worlds/gemini_demo.yaml` for a minimal demo world. The manifest controls:
- `allowed_tools` — tools visible in this world (all others are ABSENT)
- `capabilities` — per-capability allow/deny flags
- `taint_rules` — block external side effects from untrusted sources
- `side_effects` — restrict external actions

```yaml
world_id: gemini_demo

allowed_tools:
  - read_logs
  - investigate_incident

capabilities:
  read_logs:
    allowed: true
  send_email:
    allowed: false   # present in catalog; absent in this world

taint_rules:
  - tainted_external: deny

side_effects:
  external: restricted
```
