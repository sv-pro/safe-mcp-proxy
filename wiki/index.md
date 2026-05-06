# Wiki Index

Content-oriented catalog of all pages in this wiki.

## Concept Pages

| Page | Description |
|------|-------------|
| [[absent-deny]] | Ontology (Layer 1) vs Policy (Layer 2): ABSENT (does not exist) vs DENY (action blocked) |
| [[effect-virtualization]] | Layer 3: effect modes (EXECUTE / SIMULATE / PROXY / SANITIZE / TRUNCATE / DEFER); why SIMULATE is not a policy decision |
| [[ask-approval]] | ASK decision — provisional approval gate, lifecycle, execution modes, API endpoints |
| [[world-manifest]] | `world_manifest.yaml` as the sole policy surface — allowlist, capabilities, taint rules |
| [[policy-engine]] | Six deterministic decision paths evaluated in fixed order |
| [[provenance-taint]] | Source channel tracking and taint propagation through tool output chains |
| [[descriptor-drift]] | SHA256 schema integrity — detecting runtime tool descriptor mutations |
| [[audit-replay]] | Append-only audit log and forensic policy replay |
| [[architecture]] | Full pipeline overview: Provenance → Registry → PolicyEngine → Executor |

## Source Pages

### Top level

| Page | Description |
|------|-------------|
| [[src/index]] | Project root — entry points, configuration files, world manifests |
| [[src/demos/index]] | Canonical runnable demo tree |

### `safe_mcp_proxy/` package

| Page | Description |
|------|-------------|
| [[src/safe_mcp_proxy/index]] | Main package overview |
| [[src/safe_mcp_proxy/main]] | CLI entrypoint and `build_executor()` wiring function |
| [[src/safe_mcp_proxy/executor]] | Pipeline orchestrator and append-only audit logging |
| [[src/safe_mcp_proxy/registry]] | Tool definitions, allowlist filtering, and handler dispatch |
| [[src/safe_mcp_proxy/policy_engine]] | Pure Python decision logic — five ordered policy checks |
| [[src/safe_mcp_proxy/provenance]] | `Provenance` dataclass — source channel and taint tracking |
| [[src/safe_mcp_proxy/descriptor]] | SHA256 schema normalization and hash validation |
| [[src/safe_mcp_proxy/compiler]] | World manifest YAML parser — produces typed runtime config |
| [[src/safe_mcp_proxy/decision]] | `Decision` enum: ALLOW, DENY, ABSENT, SIMULATE, ASK |
| [[src/safe_mcp_proxy/simulate]] | Mock external action handler for tests and demos |
| [[src/safe_mcp_proxy/trace_store]] | Read-only streaming filter over the audit JSONL log |
| [[src/safe_mcp_proxy/bundle_replay]] | Offline bundle replayer for saved demo artifacts |
| [[src/safe_mcp_proxy/opa_engine]] | OPA/Rego drop-in replacement for `PolicyEngine` |
| [[src/safe_mcp_proxy/approval_store]] | In-memory approval token store — pending/approved/rejected/executed lifecycle |
| [[src/safe_mcp_proxy/execution_mode]] | `ExecutionMode` enum: INTERACTIVE vs BACKGROUND — controls ASK behavior |
| [[src/safe_mcp_proxy/capability_dsl]] | Parameterized capability DSL — value sources, `CapabilityDef`, manifest parser |
| [[src/safe_mcp_proxy/skill_registry]] | External skill source registry — import and catalogue skills without auto-exposing them |
| [[src/safe_mcp_proxy/capability_projection]] | Deterministic capability projection engine — `ProjectionContext`, `ProjectionResult`, `CapabilityProjectionEngine` |

### Sub-packages

| Page | Description |
|------|-------------|
| [[src/safe_mcp_proxy/config/index]] | `config/` — `policy.yaml` and per-world YAML manifests |
| [[src/safe_mcp_proxy/examples/index]] | `safe_mcp_proxy/examples/` compatibility wrappers |
| [[src/safe_mcp_proxy/scenarios/index]] | `scenarios/` — registered, runnable test scenarios |
| [[src/safe_mcp_proxy/policies/index]] | `policies/` — OPA Rego policy and tests |
| [[src/safe_mcp_proxy/atlassian/index]] | `atlassian/` — Atlassian MCP passthrough subpackage |
| [[src/safe_mcp_proxy/integrations/index]] | `integrations/` — external LLM runtime adapters |

### Other packages

| Page | Description |
|------|-------------|
| [[src/api/index]] | FastAPI HTTP layer — traces, replay, scenarios, compare, export |
| [[src/tests/index]] | Test suite overview |
| [[src/attacks/index]] | Attack corpus — YAML/MD scenarios and loader for the MCPZero Demo (EPIC 11) |
| [[src/mcpzero/index]] | MCPZero Demo package — baseline vs protected run pipeline, verdict, metrics |
| [[src/demos/index]] | Demo catalog, canonical commands, and migrated demo assets |

### `demos/`

| Page | Description |
|------|-------------|
| [[src/demos/core]] | Minimal policy-path demo scripts |
| [[src/demos/integrations]] | Claude Code, Gemini, and Atlassian integration demos |
| [[src/demos/product]] | Dashboard demo and web launcher |
| [[src/demos/narratives]] | ZombieAgent narrative demo |
| [[src/demos/safe_skills]] | Safe Skills Projection demo |
| [[src/demos/mcpzero]] | MCPZero wrapper and notebook assets |
| [[src/demos/assets]] | VHS tapes and generated demo media |

## Meta Pages

| Page | Description |
|------|-------------|
| `schema.md` | Wiki conventions, page types, update workflow |
| `index.md` | This file |
| `log.md` | Append-only ingest/query/lint history |
| `publishing.md` | How to build and deploy the wiki as a static site (Vercel, GitHub Pages) |
