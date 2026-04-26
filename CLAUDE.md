# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**safe-mcp-proxy** is a minimal, deterministic control plane for the Model Context Protocol (MCP) that constrains tool exposure and execution to mitigate runtime supply-chain risks. It is a productized MCP spinoff of [Agent Hypervisor](https://github.com/sv-pro/agent-hypervisor) — the author's experimental research playground where all ideas about agent security are explored (whitepapers, ADRs, benchmarks, full reference implementation). When working on an approach not fully specified here, check agent-hypervisor first for prior art, design decisions, and implementation patterns.

Core design principle: *"Some actions are denied. Others do not exist."*

- `ABSENT` — the tool/capability is hidden from this world (not in allowlist or capability disabled)
- `DENY` — a visible action was blocked by policy (taint violation or descriptor drift)

## Commands

```bash
# Run tests
python -m unittest tests.test_proxy

# Run a single test
python -m unittest tests.test_proxy.TestProxy.test_benign_cli_read_allows

# CLI entrypoint
python -m safe_mcp_proxy.main --tool read_file --source cli --payload '{"path":"README.md"}'

# Run demo scenarios
python -m safe_mcp_proxy.examples.benign_flow
python -m safe_mcp_proxy.examples.prompt_injection
python -m safe_mcp_proxy.examples.poisoned_descriptor
python -m safe_mcp_proxy.examples.absent_tool_case
```

There is no build step. Dependencies are PyYAML plus the Python standard library only.

## Architecture

The executor orchestrates all components in a fixed pipeline for every tool invocation:

```
Request (tool name + payload + source)
  ↓
Provenance  — marks source channel as tainted (email/web/tool_output) or clean (cli)
  ↓
Registry    — filters tool list against world_manifest.yaml allowlist → ABSENT if missing
  ↓
PolicyEngine — five deterministic decision paths (see below)
  ↓
Executor    — calls tool handler or simulate_external(); writes to audit.jsonl
```

### Policy decision paths (policy_engine.py)

All decisions are deterministic and evaluated in order:

1. **ABSENT / tool_not_allowlisted** — tool not in registry allowlist
2. **ABSENT / capability_not_allowed** — capability flag disabled in world manifest
3. **DENY / descriptor_drift** — SHA256 of current schema ≠ stored hash (schema was mutated at runtime)
4. **DENY / tainted_external_side_effect** — payload originated from an untrusted channel (email/web/tool_output) and the tool has an external side effect
5. **ALLOW / default_allow** — all checks pass

### Key modules

| Module | Role |
|---|---|
| `executor.py` | Orchestrates all components; append-only audit logging |
| `registry.py` | Holds mock tools; filters to allowlist from world manifest |
| `policy_engine.py` | Pure decision logic; returns `(decision, rule)` tuple |
| `provenance.py` | `Provenance` dataclass — tracks `source_channel` and `parent_sources`; `derive()` propagates taint through tool output |
| `descriptor.py` | SHA256 hashes tool schemas (JSON-normalized) for drift detection |
| `compiler.py` | Parses `world_manifest.yaml` into typed config (allowlist, capability_map, taint_rules, side_effect_policy) |
| `simulate.py` | Stands in for real external calls during tests/demos |
| `main.py` | CLI arg parsing; `build_executor()` wires all components together |

### Configuration

**`world_manifest.yaml`** (repo root) — the primary policy surface: declares which tools are allowlisted, which capabilities are enabled, taint rules, and side-effect policy.

**`safe_mcp_proxy/config/policy.yaml`** — controls whether external side effects are simulated (`simulation.external_side_effects: true`).

### Audit log

Every decision is appended to `safe_mcp_proxy/logs/audit.jsonl` in JSON lines format with fields: `decision`, `rule`, `tool`, `source_channel`, `taint`, `descriptor_hash`, `timestamp` (ISO-8601 UTC).

### Adding a new tool

1. Add a `ToolRecord` entry to the `TOOLS` list in `registry.py` with name, capability, schema, descriptor_hash (compute via `descriptor.hash_schema()`), side_effect_type, and handler.
2. Add the tool name to `allowed_tools` and the capability under `capabilities` in `world_manifest.yaml`.
3. Add a test in `tests/test_proxy.py` using a temp audit file and `simulate_external=True`.

## Wiki

`wiki/` is a persistent AI-maintained knowledge base (LLM Wiki pattern). Use it as a primary reference for architecture, design decisions, and module behavior — synthesized wiki pages are faster to consume than raw source files.

**When starting work on any non-trivial task**, read `wiki/index.md` first to locate relevant pages, then read those pages before writing code or making design decisions.

**Concept pages by topic:**
- `wiki/absent-deny.md` — before any policy or decision logic changes
- `wiki/architecture.md` — before any pipeline changes
- `wiki/policy-engine.md` — before modifying `policy_engine.py` or `opa_engine.py`
- `wiki/provenance-taint.md` — before modifying `provenance.py`
- `wiki/descriptor-drift.md` — before modifying `descriptor.py`
- `wiki/world-manifest.md` — before modifying world manifests or `compiler.py`
- `wiki/audit-replay.md` — before modifying `executor.py` or `trace_store.py`

**After making significant changes** (new module, changed behavior, new policy path): update affected wiki pages following `wiki/schema.md` conventions and append an entry to `wiki/log.md`.

## Roadmap & "What's next?"

When asked **"what's next?"**, **"что дальше?"**, **"next issue"**, **"next task"**, or similar:

1. Fetch open issues: use `mcp__github__list_issues` with `owner=sv-pro`, `repo=safe-mcp-proxy`, `state=OPEN`.
2. Pick the highest-priority open issue from the highest EPIC number.
3. Report the issue number, title, and task list before starting work.

Issues live at: https://github.com/sv-pro/safe-mcp-proxy/issues

- **Open** = work remaining (EPICs 8–9)
- **Closed** = already implemented (EPICs 0–7)
- Labels: `epic/N-*`, `type/*`, `priority/*`
