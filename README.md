# safe-mcp-proxy

A minimal, deterministic control plane for MCP that constrains tool exposure and execution to mitigate runtime supply-chain risks.

## Problem

MCP (Model Context Protocol) enables agents to discover and call tools at runtime. The agent receives a tool list it didn't choose — it trusts whatever the connected MCP server advertises. This creates a runtime supply-chain attack surface:

- A compromised or malicious MCP server can inject tools with deceptive schemas.
- A tool schema can be mutated between startup and invocation — the agent calls what it thinks is `read_file`, but the schema has silently changed.
- Prompt injection via web pages, emails, or tool output can instruct an agent to call any tool that exists in its registry.

Standard input filters don't fix this. If the tool exists and the agent can see it, the agent can call it. The attack surface is the tool list itself.

## Solution

safe-mcp-proxy is a narrow control plane that sits between the agent and the tool registry. Nothing reaches the agent without passing through it.

- **Static world manifest** — `world_manifest.yaml` is the sole policy surface. It declares which tools exist, which capabilities are enabled, and what taint rules apply. It is compiled once at startup; the runtime config is immutable.
- **Taint / provenance tracking** — every request carries a source channel. Channels like `email`, `web`, and `tool_output` are marked tainted. Taint propagates through tool output chains.
- **Descriptor drift detection** — each tool's schema is SHA256-hashed at registration time. Any runtime mutation of a schema is detected and blocked before execution.
- **Append-only audit log** — every decision (ALLOW, DENY, ABSENT) is written to `audit.jsonl` with enough fields for deterministic forensic replay.

## Key idea

> Some actions are denied. Others do not exist.

There are two distinct outcomes when a tool call is blocked:

| Outcome | Meaning |
|---|---|
| `ABSENT` | The tool/capability is hidden from this world. It was never offered to the agent. |
| `DENY` | A visible action was blocked by policy — taint violation or descriptor drift. |

This distinction matters. An agent that cannot see a tool cannot be manipulated into calling it. ABSENT is stronger than DENY.

**[Agent Hypervisor](https://github.com/sv-pro/agent-hypervisor) spinoff:** safe-mcp-proxy is a productized MCP spinoff of Agent Hypervisor — the author's experimental research playground that explores the full four-layer agent security architecture (execution isolation → base ontology → dynamic ontology → execution governance). safe-mcp-proxy distills Layers 1–3 into a minimal, production-grade MCP control plane. The agent-hypervisor repo is the upstream reference: consult it for whitepapers, ADRs, deeper design decisions, and implementation patterns not covered here. The agent sees only the world the manifest defines. Tools absent from the manifest do not exist in that world; they cannot be denied because they were never offered.

## Architecture

Every tool invocation passes through a fixed pipeline:

```
Request (tool name + payload + source)
  ↓
Provenance  — marks source channel as tainted (email/web/tool_output) or clean (cli)
  ↓
Registry    — filters tool list against world_manifest.yaml allowlist → ABSENT if missing
  ↓
PolicyEngine — five deterministic decision paths (evaluated in order)
  ↓
Executor    — calls tool handler or simulate_external(); writes to audit.jsonl
```

### Modules

| Module | Role |
|---|---|
| `executor.py` | Orchestrates the pipeline; append-only audit logging; deterministic `replay()` |
| `registry.py` | Holds mock tool definitions; filters to allowlist from world manifest |
| `policy_engine.py` | Pure decision logic — returns `(decision, rule)` tuple; no side effects |
| `provenance.py` | `Provenance` dataclass; `from_source()` marks taint; `derive()` propagates through chains |
| `descriptor.py` | SHA256-hashes tool schemas (JSON-normalized) for drift detection |
| `compiler.py` | Parses `world_manifest.yaml` into typed runtime config (immutable after startup) |
| `simulate.py` | Stands in for real external calls during tests and demos |
| `main.py` | CLI arg parsing; `build_executor()` wires all components together |

### Policy decision paths

All five paths are evaluated in order; the first match wins:

| # | Decision | Rule | Condition |
|---|---|---|---|
| 1 | ABSENT | `tool_not_allowlisted` | Tool name not in the world's allowlist |
| 2 | ABSENT | `capability_not_allowed` | Capability flag disabled in world manifest |
| 3 | DENY | `descriptor_drift` | SHA256 of current schema ≠ stored hash |
| 4 | DENY | `tainted_external_side_effect` | Payload from tainted channel + tool has external side effect |
| 5 | ALLOW | `default_allow` | All checks pass |

## Configuration

`world_manifest.yaml` (repo root) is the primary policy surface:

```yaml
world_id: "default"

# Only tools listed here are visible to the agent
allowed_tools:
  - read_file
  - list_repo
  - send_email

# Per-capability enable/disable flags
capabilities:
  read_file:
    allowed: true
  list_repo:
    allowed: true
  send_email:
    allowed: true
  dangerous_exec:
    allowed: false   # capability disabled → ABSENT even if tool were allowlisted

# Taint policy: deny external side effects from tainted sources
taint_rules:
  - tainted_external: deny

side_effects:
  external: restricted
```

### World model

`world_manifest.yaml` is the **static world definition** — compiled once at startup into an immutable runtime config. There is no other policy surface.

| Concept | Role | Mutability |
|---|---|---|
| `world_manifest.yaml` | World definition | Static (file on disk) |
| compiled config | World runtime | Immutable after startup |
| `world_id` | World identifier | Declared in manifest |

Multiple worlds are supported via `safe_mcp_proxy/config/worlds/` (with legacy fallback to `worlds/`). Pass `--world <world_id>` to load `safe_mcp_proxy/config/worlds/<world_id>.yaml` instead of the default manifest.

## Demo

**Prompt injection → DENY** — a request arriving from a tainted channel (`web`) that targets a tool with an external side effect is blocked before execution:

![injection → DENY](demos/assets/injection.gif)

**Absent tool → "does not exist"** — a tool not listed in the world manifest is invisible; the agent receives no denial, just absence:

![absent tool](demos/assets/absent.gif)

> GIFs are generated from VHS tape files in `demos/assets/tapes/`.
> To regenerate: install [VHS](https://github.com/charmbracelet/vhs) and run `bash demos/assets/generate_gifs.sh`.

## Quick start

No build step. Runtime dependencies for the CLI, demos, and optional HTTP API
are listed in `requirements.txt`.

```bash
pip install -r requirements.txt
```

Run the four core demo scenarios:

```bash
python -m demos.core.benign_flow
python -m demos.core.prompt_injection
python -m demos.core.poisoned_descriptor
python -m demos.core.absent_tool_case
```

See [demos/README.md](demos/README.md) for the full demo catalog. Legacy
commands under `safe_mcp_proxy.examples` still work as wrappers.

Or call the CLI entrypoint directly:

```bash
python -m safe_mcp_proxy.main --tool read_file --source cli --payload '{"path":"README.md"}'
```

Run the HTTP API locally:

```bash
uvicorn api.main:app --reload
```

Available endpoints:

```text
GET /traces?limit=N
GET /traces/{id}
GET /stats
POST /replay/{id}
```

Run the test suite:

```bash
python -m unittest tests.test_proxy tests.test_trace_store tests.test_api
```

## Example outputs

### Scenario 1 — Normal flow (ALLOW)

Clean CLI request for `read_file`:

```json
{
  "decision": "ALLOW",
  "rule": "default_allow",
  "result": {
    "ok": true,
    "content": "mock-read:README.md"
  }
}
```

### Scenario 2 — Prompt injection attempt (DENY)

`send_email` called from a tainted `web` source. The tool has an external side effect; the taint rule blocks it:

```json
{
  "decision": "DENY",
  "rule": "tainted_external_side_effect",
  "result": {
    "error": "Denied by policy",
    "reason": "tainted_external_side_effect"
  }
}
```

### Scenario 3 — Poisoned tool descriptor (DENY)

A tool schema is mutated at runtime (an extra field is injected). The stored SHA256 no longer matches; execution is blocked before the handler is called:

```json
{
  "decision": "DENY",
  "rule": "descriptor_drift",
  "result": {
    "error": "Denied by policy",
    "reason": "descriptor_drift"
  }
}
```

### Scenario 4 — Absent tool (ABSENT)

`dangerous_exec` is not in the allowlist. The agent never sees it; attempting to call it is treated as if the tool does not exist:

```json
{
  "decision": "ABSENT",
  "rule": "tool_not_allowlisted",
  "result": {
    "error": "Action does not exist in this world"
  }
}
```

## Audit log

Every decision is appended to `safe_mcp_proxy/logs/audit.jsonl` in JSON lines format:

```jsonl
{"decision": "ALLOW", "rule": "default_allow", "tool": "read_file", "source_channel": "cli", "taint": false, "descriptor_hash": "53582d9d...", "timestamp": "2026-04-22T07:08:51.769899+00:00"}
{"decision": "DENY", "rule": "tainted_external_side_effect", "tool": "send_email", "source_channel": "web", "taint": true, "descriptor_hash": "45dfabdd...", "timestamp": "2026-04-22T07:08:51.819637+00:00"}
{"decision": "ABSENT", "rule": "tool_not_allowlisted", "tool": "dangerous_exec", "source_channel": "cli", "taint": false, "descriptor_hash": "", "timestamp": "2026-04-22T07:08:51.918637+00:00"}
```

`executor.replay(audit_entry)` reconstructs the same decision deterministically from any audit record — every policy decision is reproducible for forensic verification.

> **Note:** `safe_mcp_proxy/logs/` is gitignored — the live log is a runtime artifact, not source.
> The API seeds it automatically from `seeds/demo.jsonl` on first start when the file is absent or empty.

## Atlassian MCP Proxy

A policy-enforcing passthrough for the [Atlassian Remote MCP Server](https://mcp.atlassian.com). It sits between an AI agent and Atlassian tools (Jira, Confluence) and enforces four layers of control on every `tools/call`:

| Layer | What it does |
|---|---|
| Allowlist (ABSENT) | Tools not in the manifest are invisible to the agent |
| Taint gate (DENY) | Requests from untrusted channels cannot call write tools |
| Data-flow rules (DENY) | Raw Confluence content cannot flow into Jira write calls |
| Arg rules (DENY) | `jira_create_issue` is restricted to approved project keys |

### Quick setup

```bash
# 1. Configure
cp .env.example .env
#    Set ATLASSIAN_MCP_URL, ATLASSIAN_MANIFEST_PATH, etc.

# 2a. Run with Docker
docker build -t safe-mcp-proxy .
docker run --env-file .env -p 8000:8000 safe-mcp-proxy

# 2b. Run locally
pip install pyyaml fastapi "uvicorn[standard]"
uvicorn api.main:app --reload
```

The proxy exposes two endpoints:

```text
POST /atlassian/mcp     — MCP JSON-RPC passthrough (policy-gated)
GET  /atlassian/config  — Active config (no secrets)
```

### Audit log

Every request, policy decision, and response is appended to
`safe_mcp_proxy/logs/atlassian_requests.jsonl`. Each entry carries a
`trace_id` (UUID) so request → decision → response entries can be
correlated:

```jsonl
{"direction":"request",  "trace_id":"a1b2...", "timestamp":"...", "payload":{...}}
{"direction":"decision", "trace_id":"a1b2...", "timestamp":"...", "tool":"jira_create_issue", "decision":"DENY", "rule":"no_raw_confluence_to_jira", "tainted":false, "flow_labels":["confluence_raw"]}
{"direction":"response", "trace_id":"a1b2...", "timestamp":"...", "payload":{...}}
```

Inspect the audit log with the built-in CLI:

```bash
# List recent decisions
python -m safe_mcp_proxy.atlassian.cli list --last 20

# Show only blocked calls
python -m safe_mcp_proxy.atlassian.cli list --decision DENY

# Show all entries for one trace
python -m safe_mcp_proxy.atlassian.cli trace --trace-id a1b2c3d4
```

### Policy manifest

The manifest at `manifests/atlassian_mvp.yaml` is the sole policy surface.
Set `ATLASSIAN_MANIFEST_PATH` to point to it (or a custom manifest):

```yaml
allowed_tools:
  - jira_get_issue
  - jira_create_issue
  - confluence_get_page

external_write_tools:
  - jira_create_issue

arg_rules:
  jira_create_issue:
    - arg: project_key
      allowed_values: [SAFE, TEST, DEMO]
      rule: jira_create_restricted_projects

data_flow_rules:
  - if_label: confluence_raw
    deny_for: [jira_create_issue, jira_update_issue, jira_add_comment]
    rule: no_raw_confluence_to_jira
```

See [docs/atlassian-quickstart.md](docs/atlassian-quickstart.md) and
[demos/integrations/README.md](demos/integrations/README.md) for the full
attack-and-block scenario.

## Adding a new tool

1. Add a `ToolRecord` entry to `TOOLS` in `registry.py` — set `name`, `capability`, `schema`, `descriptor_hash` (compute via `descriptor.hash_schema()`), `side_effect_type`, and `handler`.
2. Add the tool name to `allowed_tools` and its capability under `capabilities` in `world_manifest.yaml`.
3. Add a test in `tests/test_proxy.py` using a temp audit file and `simulate_external=True`.

## File layout

```text
safe_mcp_proxy/
  main.py           CLI entrypoint; build_executor() wiring
  executor.py       Pipeline orchestration; audit logging; replay
  registry.py       Tool definitions; allowlist filtering
  policy_engine.py  Decision logic (pure, no side effects)
  provenance.py     Taint tracking and propagation
  descriptor.py     SHA256 schema hashing
  compiler.py       world_manifest.yaml → typed runtime config
  capability_dsl.py Parameterized capability definitions — LiteralSource, ActorInputSource
  simulate.py       External call stub for tests and demos
  config/
    policy.yaml     Simulation flag (external_side_effects: true/false)
  examples/         Compatibility wrappers; canonical demos live in demos/
  logs/             gitignored — runtime output only
    audit.jsonl     (created on first run; seeded from seeds/demo.jsonl by the API)
demos/
  README.md         Demo catalog
  core/             Minimal policy-path demos
  integrations/     Claude Code, Gemini, Atlassian demos
  product/          Dashboard demo and launcher
  narratives/       ZombieAgent narrative demo
  safe_skills/      Skills supply-chain/capability projection demo
  mcpzero/          MCPZero launcher wrapper and notebook assets
seeds/
  demo.jsonl        Curated demo audit entries (committed; used as API seed data)
worlds/
  repo_assistant.yaml
  read_only.yaml
world_manifest.yaml  Primary policy surface
tests/
  test_proxy.py
```
