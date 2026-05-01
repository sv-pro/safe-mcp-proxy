# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**safe-mcp-proxy** is a minimal, deterministic control plane for the Model Context Protocol (MCP) that constrains tool exposure and execution to mitigate runtime supply-chain risks. It is a productized MCP spinoff of [Agent Hypervisor](https://github.com/sv-pro/agent-hypervisor) — the author's experimental research playground where all ideas about agent security are explored (whitepapers, ADRs, benchmarks, full reference implementation). When working on an approach not fully specified here, check agent-hypervisor first for prior art, design decisions, and implementation patterns.

Core design principle: *"Some actions are denied. Others do not exist."*

- `ABSENT` — the tool/capability is hidden from this world (not in allowlist or capability disabled)
- `DENY` — a visible action was blocked by policy (taint violation or descriptor drift)
- `ASK` — a visible action requires human approval before execution (pauses in INTERACTIVE mode; becomes DENY in BACKGROUND mode)

## Commands

```bash
# Run all tests
python -m unittest tests.test_proxy

# Run a single test
python -m unittest tests.test_proxy.TestProxy.test_benign_cli_read_allows

# CLI entrypoint (--engine python|opa; --mode interactive|background; --world <world_id>)
python -m safe_mcp_proxy.main --tool read_file --source cli --payload '{"path":"README.md"}'
python -m safe_mcp_proxy.main --tool send_email --source web --payload '{}' --engine opa
python -m safe_mcp_proxy.main --tool send_email --source cli --payload '{}' --mode background

# Run built-in demo scenarios
python -m safe_mcp_proxy.examples.benign_flow
python -m safe_mcp_proxy.examples.prompt_injection
python -m safe_mcp_proxy.examples.poisoned_descriptor
python -m safe_mcp_proxy.examples.absent_tool_case
python -m safe_mcp_proxy.examples.ask_modes
python -m safe_mcp_proxy.examples.atlassian_demo
python -m safe_mcp_proxy.examples.deterministic_replay

# Offline bundle replay (policy drift detection)
python -m safe_mcp_proxy.bundle_replay path/to/bundle.json

# MCPZero attack prevention demo
python -m mcpzero.demo --scenario email_injection
python -m mcpzero.demo --scenario tool_chain --output ./results/

# Start FastAPI server
uvicorn api.main:app --reload
```

There is no build step. Core dependencies are PyYAML and the Python standard library. The FastAPI server additionally requires `fastapi` and `uvicorn`. OPA engine mode requires the `opa` binary on PATH.

## Architecture

The executor orchestrates all components in a fixed pipeline for every tool invocation:

```
Request (tool name + payload + source + mode)
  ↓
Provenance  — marks source channel as tainted (email/web/tool_output) or clean (cli);
              carries ExecutionMode (INTERACTIVE | BACKGROUND)
  ↓
Registry    — filters tool list against world_manifest.yaml allowlist → ABSENT if missing
  ↓
PolicyEngine — six deterministic decision paths (see below)
  ↓
Executor    — ALLOW: calls tool handler or simulate_external()
              ASK: creates approval token (INTERACTIVE) or returns DENY (BACKGROUND)
              DENY/ABSENT: returns immediately
  ↓
Audit       — appends to audit.jsonl regardless of outcome
```

### Policy decision paths

All decisions are deterministic and evaluated in order. Both the Python engine (`policy_engine.py`) and the OPA/Rego engine (`opa_engine.py` + `policies/proxy.rego`) implement the same six rules:

1. **ABSENT / tool_not_allowlisted** — tool not in registry allowlist
2. **ABSENT / capability_not_allowed** — capability flag disabled in world manifest
3. **DENY / descriptor_drift** — SHA256 of current schema ≠ stored hash (schema was mutated at runtime)
4. **DENY / tainted_external_side_effect** — payload from untrusted channel (email/web/tool_output) and tool has external side effect
5. **ASK / approval_required** — capability has `requires_approval: true` in world manifest
6. **ALLOW / default_allow** — all checks pass

### ExecutionMode and the ASK decision

`ExecutionMode` (INTERACTIVE | BACKGROUND) controls how ASK is resolved:
- **INTERACTIVE**: Executor creates a UUID approval token via `ApprovalStore`, returns `ASK` with token. Caller must POST to `/approvals/{token}/approve` or `/approvals/{token}/reject` to resume.
- **BACKGROUND**: ASK immediately collapses to DENY (autonomous agents must not block on human input). Recorded in audit log as a single entry.

ASK produces two audit entries when fully resolved (one for the initial ask, one for the approved/rejected outcome). BACKGROUND produces one immediate deny entry.

### Key modules

| Module | Role |
|---|---|
| `executor.py` | Orchestrates pipeline; ALLOW/DENY/ASK/ABSENT dispatch; append-only audit logging |
| `registry.py` | Holds mock tools; filters to allowlist; builds scoped tools from CapabilityDef |
| `policy_engine.py` | Python-native policy; returns `(decision, rule)` tuple; six deterministic rules |
| `opa_engine.py` | OPA/Rego-backed drop-in for PolicyEngine; supports subprocess and REST modes |
| `decision.py` | `Decision` enum: ALLOW \| DENY \| ABSENT \| SIMULATE \| ASK |
| `execution_mode.py` | `ExecutionMode` enum: INTERACTIVE \| BACKGROUND |
| `provenance.py` | `Provenance` dataclass — tracks `source_channel`, `tainted`, `parent_sources`, `execution_mode`; `derive()` propagates taint |
| `descriptor.py` | SHA256 hashes tool schemas (JSON-normalized) for drift detection |
| `approval_store.py` | In-memory token store for ASK lifecycle: pending → approved/rejected → executed |
| `compiler.py` | Parses `world_manifest.yaml` into typed config; assembles OPA input document |
| `capability_dsl.py` | Parameterized capability definitions with literal/actor_input/context_ref value sources |
| `capability_projection.py` | Deterministic filtering of skill capabilities by execution context, mode, and workflow |
| `skill_registry.py` | External skill source registry; imported skills require explicit world manifest declaration |
| `trace_store.py` | Read-only audit log reader; streams and filters JSONL entries |
| `bundle_replay.py` | Offline bundle replayer for policy drift detection across saved demo traces |
| `simulate.py` | Stands in for real external calls during tests/demos |
| `main.py` | CLI arg parsing; `build_executor()` wires all components together |

### Atlassian integration (`safe_mcp_proxy/atlassian/`)

EPIC 9 adds a passthrough proxy for Atlassian Remote MCP Server (Jira/Confluence). The subpackage has its own 5-rule decision engine separate from the core pipeline:

| Module | Role |
|---|---|
| `passthrough.py` | JSON-RPC forwarding + policy enforcement + response wrapping |
| `policy.py` | `ManifestPolicyEngine` — ABSENT, taint_blocks_external, data_flow, arg_rules, default |
| `filter.py` | Allowlist/denylist composition (`CapabilityFilter`) |
| `flow.py` | Data-flow rules and context tracking (provenance lite) |
| `adapters.py` | MCP JSON-RPC request/response adapters |
| `config.py` | `AtlassianProxyConfig` — mode, allowed/denied_tools, manifest_path, source_channel |
| `trace_reader.py` | Audit trail reader for Atlassian requests |
| `cli.py` | CLI wrapper for Atlassian proxy |

The Atlassian manifest (`manifests/atlassian_mvp.yaml`) demonstrates argument validation (`arg_rules`), safe abstractions (Confluence page truncation to 500 chars), and data-flow rules blocking raw Confluence → Jira write chains.

### MCPZero attack prevention demo (`mcpzero/`)

A demonstration framework that runs attack scenarios against an unprotected baseline agent and the protected proxy, then compares verdicts:

| Module | Role |
|---|---|
| `mcpzero/agent/runner.py` | `ScenarioRunner` — runs attack in baseline or protected mode |
| `mcpzero/observer/observer.py` | `ExecutionObserver` — trace collection during runs |
| `mcpzero/verdict/engine.py` | Verdict struct with `demo_pass`/`attack_succeeded` flags |
| `mcpzero/generator/attack_gen.py` | Attack generation utilities |
| `mcpzero/metrics/reporter.py` | Metrics and summary reporter |
| `mcpzero/proxy/proxy.py` | Proxy adapter for MCPZero runner |
| `mcpzero/demo.py` | CLI entry point: `--scenario NAME`, `--no-color`, `--output DIR` |

### Attack corpus (`attacks/`)

YAML/JSON attack scenarios loaded by `attacks/loader.py`:

- `attacks/email_injection.yaml` — email-sourced prompt injection
- `attacks/tool_chain.yaml` — multi-step tool chain escalation
- `attacks/mcp_poison.json` — MCP descriptor poisoning scenario
- `attacks/schema.yaml` — scenario schema definition

Valid scenario types: `email_injection`, `tool_chain`, `mcp_poison`. Valid source channels: `cli`, `email`, `web`, `tool_output`.

### REST API (`api/main.py`)

FastAPI server exposing the full proxy surface:

| Endpoint | Description |
|---|---|
| `GET /traces` | Paginated audit log |
| `GET /replay/{trace_id}` | Re-evaluate policy against recorded entry |
| `GET /scenarios/{name}/run` | Run registered attack scenario |
| `POST /compare` | Run scenario across multiple worlds |
| `GET /export/bundle` | Export scenario + manifest + traces for offline replay |
| `GET /stats` | Decision counts (ALLOW/DENY/ABSENT/ASK/SIMULATE) |
| `GET /approvals/{token}` | Approval token status |
| `POST /approvals/{token}/approve` | Execute approved action |
| `POST /approvals/{token}/reject` | Reject pending action |
| `POST /atlassian/mcp` | Atlassian Remote MCP passthrough |
| `GET /atlassian/config` | Show Atlassian proxy configuration |

Seeds `audit.jsonl` from `seeds/demo.jsonl` on startup if log is empty.

### Configuration

**`world_manifest.yaml`** (repo root) — the primary policy surface: declares which tools are allowlisted, which capabilities are enabled, taint rules, side-effect policy, capability definitions (DSL), and approval requirements.

**`worlds/`** — named world configurations (`world_a.yaml`, `world_b.yaml`, `world_c.yaml`, `mcpzero_demo.yaml`, `read_only.yaml`, `repo_assistant.yaml`). Pass `--world <world_id>` to CLI or `build_executor(world_id=...)` to select.

**`safe_mcp_proxy/config/policy.yaml`** — controls whether external side effects are simulated (`simulation.external_side_effects: true`).

**`safe_mcp_proxy/config/worlds/`** — per-world YAML files loaded by `main.py` when resolving world IDs.

**`manifests/atlassian_mvp.yaml`** — Atlassian MVP policy manifest (EPIC 9).

### Capability DSL

`capability_dsl.py` supports parameterized capability definitions in world manifests. Argument value sources:
- `literal` — fixed value baked into the definition; invisible to actor, auto-injected at invocation
- `actor_input` — value supplied by the actor at call time; appears in the actor-visible schema
- `context_ref` — value resolved from execution context (not yet wired; raises `NotImplementedError`)

Example: `send_me_email` wraps `send_email` with `to` locked as a literal (`owner@example.com`), preventing tainted payloads from redirecting the recipient.

### Audit log

Every decision is appended to `safe_mcp_proxy/logs/audit.jsonl` in JSON Lines format with fields: `decision`, `rule`, `tool`, `source_channel`, `taint`, `descriptor_hash`, `timestamp` (ISO-8601 UTC). ASK decisions that resolve produce a second entry. The log is append-only; `trace_store.py` provides read access via `TraceStore`.

### Adding a new tool

1. Add a `ToolRecord` entry to the `TOOLS` list in `registry.py` with name, capability, schema, descriptor_hash (compute via `descriptor.hash_schema()`), side_effect_type, and handler.
2. Add the tool name to `allowed_tools` and the capability under `capabilities` in `world_manifest.yaml`.
3. Add a test in `tests/test_proxy.py` using a temp audit file and `simulate_external=True`.

### Switching policy engines

- **Python (default)**: No dependencies. Set `policy_engine: python` in manifest or pass `--engine python`.
- **OPA/Rego**: Requires `opa` binary on PATH or an OPA REST server at `http://localhost:8181`. Set `policy_engine: opa` in manifest or pass `--engine opa`. The Rego policy is at `safe_mcp_proxy/policies/proxy.rego`. Tests in `tests/test_opa_engine.py` are skipped when the `opa` binary is absent.

## Wiki

`wiki/` is a persistent AI-maintained knowledge base (LLM Wiki pattern). Use it as a primary reference for architecture, design decisions, and module behavior — synthesized wiki pages are faster to consume than raw source files.

**When starting work on any non-trivial task**, read `wiki/index.md` first to locate relevant pages, then read those pages before writing code or making design decisions.

**Concept pages by topic:**
- `wiki/absent-deny.md` — before any policy or decision logic changes
- `wiki/ask-approval.md` — before modifying approval workflow, ExecutionMode, or ASK decision
- `wiki/architecture.md` — before any pipeline changes
- `wiki/policy-engine.md` — before modifying `policy_engine.py` or `opa_engine.py`
- `wiki/provenance-taint.md` — before modifying `provenance.py`
- `wiki/descriptor-drift.md` — before modifying `descriptor.py`
- `wiki/world-manifest.md` — before modifying world manifests or `compiler.py`
- `wiki/audit-replay.md` — before modifying `executor.py` or `trace_store.py`

**Source pages** (in `wiki/src/`) mirror every module in the codebase with synthesized descriptions, key symbols, and behavioral notes.

**After making significant changes** (new module, changed behavior, new policy path): update affected wiki pages following `wiki/schema.md` conventions and append an entry to `wiki/log.md`.

## Tests

```bash
# Core proxy tests
python -m unittest tests.test_proxy

# OPA/Rego engine parity tests (requires opa binary)
python -m unittest tests.test_opa_engine

# Atlassian integration tests
python -m unittest tests.test_atlassian_policy
python -m unittest tests.test_atlassian_flow
python -m unittest tests.test_atlassian_passthrough
python -m unittest tests.test_atlassian_filter
python -m unittest tests.test_atlassian_adapters

# Attack corpus, skill, trace, and scenario tests
python -m unittest tests.test_attack_corpus
python -m unittest tests.test_skill_registry
python -m unittest tests.test_trace_store
python -m unittest tests.test_scenarios
python -m unittest tests.test_capability_projection

# API and MCPZero tests
python -m unittest tests.test_api
python -m unittest tests.test_mcpzero

# Run all tests
python -m unittest discover tests
```

All tests use temp audit files and `simulate_external=True` to avoid side effects.

## Roadmap & "What's next?"

When asked **"what's next?"**, **"что дальше?"**, **"next issue"**, **"next task"**, or similar:

1. Fetch open issues: use `mcp__github__list_issues` with `owner=sv-pro`, `repo=safe-mcp-proxy`, `state=OPEN`.
2. Pick the highest-priority open issue from the highest EPIC number.
3. Report the issue number, title, and task list before starting work.

Issues live at: https://github.com/sv-pro/safe-mcp-proxy/issues

- **Open** = work remaining (EPICs 8–9)
- **Closed** = already implemented (EPICs 0–7)
- Labels: `epic/N-*`, `type/*`, `priority/*`
