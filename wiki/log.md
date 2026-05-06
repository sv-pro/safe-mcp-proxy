# Wiki Log

Append-only record of ingests, queries, and maintenance operations.

---

## 2026-05-05 — Demo tree synchronization

- Added `wiki/src/demos/` source pages for the canonical demo tree:
  `index`, `core`, `integrations`, `product`, `narratives`, `safe_skills`,
  `mcpzero`, and `assets`.
- Updated `wiki/src/index.md` and `wiki/index.md` so demos are represented as a
  first-class top-level source tree rather than as `safe_mcp_proxy/examples/`.
- Reframed `wiki/src/safe_mcp_proxy/examples/index.md` as compatibility
  wrappers that delegate to `demos/`.
- Updated MCPZero and attacks wiki pages to distinguish framework code and
  shared attack corpus from runnable demo entry points.
- Updated `wiki/meta.yaml` sync metadata for the demo refactor.

---

## 2026-05-03 — EPIC 12 complete: real MCP server (Claude Code integration)

Three new source pages for the MCP transport layer:

- `wiki/src/safe_mcp_proxy/mcp_server.md` *(new)* — `MCPProxyServer`, decision mapping (ALLOW/DENY/ABSENT/ASK → MCP response/error), CLI entry point, provenance notes
- `wiki/src/safe_mcp_proxy/mcp_test_server.md` *(new)* — minimal upstream server with 4 mock tools; side-effect table; used by integration tests and demo
- `wiki/src/safe_mcp_proxy/mcp_upstream.md` *(new)* — `UpstreamConnector` lifecycle, `call_tool()` forwarding, ALLOW-path-only invariant
- `wiki/src/safe_mcp_proxy/index.md` — added three new module rows

All 15 tests in `tests/test_mcp_server.py` green. Demo (`examples/claude_code_demo.py`) verified 4 guarantees: tool surface control, taint blocking, absent tools, upstream forwarding.

---

## 2026-05-03 — Three-layer model: Ontology / Policy / Effect Virtualization

Reformulated the architectural model from a flat decision pipeline to three independent layers. Updated four pages and created one new page:

- `wiki/effect-virtualization.md` *(new)* — Layer 3 concept page: effect modes (EXECUTE / SIMULATE / PROXY / SANITIZE / TRUNCATE / DEFER), security motivation (no boundary-learning signal), relationship to sandboxing, current implementation state
- `wiki/absent-deny.md` — reframed ABSENT as Ontology Layer (Layer 1), DENY as Policy Layer (Layer 2); replaced old "Open question" section with reference to `[[effect-virtualization]]`
- `wiki/architecture.md` — pipeline updated to show three layers; Executor dispatch section expanded with effect mode breakdown
- `wiki/policy-engine.md` — noted that rules 1–2 are ontological (Layer 1) and rules 3–4 are policy (Layer 2)
- `wiki/index.md` — added `[[effect-virtualization]]` to concept page table

---

## 2026-05-01 — Full wiki sync against HEAD (6e82b9c); metadata file added

Audited the entire wiki against the current codebase. Added `wiki/meta.yaml` to track commit hash and timestamp of each sync so future updates can use `git log <commit>..HEAD` to scope the diff.

**New pages created (11):**
- `wiki/src/safe_mcp_proxy/atlassian/index.md` — subpackage overview and pipeline diagram
- `wiki/src/safe_mcp_proxy/atlassian/passthrough.md` — `MCPPassthrough` pipeline orchestrator
- `wiki/src/safe_mcp_proxy/atlassian/policy.md` — `ManifestPolicyEngine` five-rule decision engine
- `wiki/src/safe_mcp_proxy/atlassian/filter.md` — `CapabilityFilter` allowlist/denylist for `tools/list`
- `wiki/src/safe_mcp_proxy/atlassian/flow.md` — `FlowContext`, `DataFlowRule`, data-label tracking
- `wiki/src/safe_mcp_proxy/atlassian/adapters.md` — `ATLASSIAN_TOOLS` registry + `apply_safe_abstraction`
- `wiki/src/safe_mcp_proxy/atlassian/config.md` — `AtlassianProxyConfig` and env-var loading
- `wiki/src/safe_mcp_proxy/atlassian/trace_reader.md` — `AtlassianTraceReader`, `TraceEntry`
- `wiki/src/safe_mcp_proxy/atlassian/cli.md` — trace log CLI inspector
- `wiki/src/safe_mcp_proxy/integrations/index.md` — integrations subpackage overview
- `wiki/src/safe_mcp_proxy/integrations/gemini_adapter.md` — `GeminiAdapter`, `ToolCall`

**Pages updated:**
- `wiki/src/safe_mcp_proxy/policy_engine.md` — corrected "5 rules" → "6 rules"; added `approval_required` to `__init__` symbol table; added rule 5 (ASK / approval_required) to evaluation order
- `wiki/src/safe_mcp_proxy/index.md` — added atlassian and integrations sub-package rows
- `wiki/index.md` — added atlassian and integrations source page rows
- `wiki/src/tests/index.md` — expanded file table to include all 21 test files (was 6); fixed "5 decision paths" → "6 decision paths"

**New file:**
- `wiki/meta.yaml` — tracks commit hash, timestamp, branch, updated_by, coverage_note for each sync

---

## 2026-04-26 — Wiki audit: EPIC 11 full coverage

- Updated `wiki/src/attacks/index.md` — added `tool_chain.yaml` and `mcp_poison.json` to layout table
- Updated `wiki/src/attacks/loader.md` — added `poison_tool` field to AttackScenario table; documented JSON support in `load()` and `load_all()`; updated "Used by" to reflect actual callers
- Created `wiki/src/mcpzero/agent.md` — `BaselineAgent`: step result dict schema, ALLOW/ABSENT logic, no-policy invariant
- Created `wiki/src/mcpzero/runner.md` — `ScenarioRunner`, `RunResult`, mode switch semantics, observer wiring, `load_scenario()`
- Created `wiki/src/mcpzero/generator.md` — `generate()`, tool graph strategy, output format, future CI use
- Created `wiki/src/mcpzero/observer.md` — `ExecutionObserver`, trace entry schema, wiring pattern, gitignore note
- Updated `wiki/src/mcpzero/index.md` — layout table now links to all submodule pages; See also expanded

---

## 2026-04-26 — EPIC 11 / I3–I15: full MCPZero demo pipeline

- Updated `wiki/src/attacks/index.md` and `wiki/src/attacks/loader.md` — added tool_chain + mcp_poison scenarios; JSON loader support; poison_tool field
- Created `wiki/src/mcpzero/index.md` — package overview: layout, entry point, data flow diagram, world manifest note
- Created `wiki/src/mcpzero/proxy.md` — SafeMCPProxy symbols, normalised result dict, mcp_poison handling, descriptor drift link
- Created `wiki/src/mcpzero/verdict.md` — StepVerdict/Verdict symbols, proxy_blocked semantics (at-least-one not all), metrics reporter symbols
- Updated `wiki/index.md` — added `[[src/mcpzero/index]]` row
- Updated `wiki/src/index.md` — added `[[src/mcpzero/index]]` row

---

## 2026-04-26 — EPIC 11 / I1–I2: attack corpus structure + email injection scenario

- Created `wiki/src/attacks/index.md` — package overview: layout table, two scenario formats (YAML structured vs Markdown documents), cross-links
- Created `wiki/src/attacks/loader.md` — source page: AttackStep, AttackScenario fields, load/load_document/load_all symbols, validation rules, document inlining behaviour
- Updated `wiki/index.md` — added `[[src/attacks/index]]` row under "Other packages"
- Updated `wiki/src/index.md` — added `[[src/attacks/index]]` row under Packages

---

## 2026-04-26 — EPIC 10 / I7: positioning doc (PR claude/safe-skills-epic-s5Y88)

- Created `docs/safe_skills_projection.md` — 334-line positioning doc covering: dynamic skills as capability space, supply-chain risk model, indirect prompt injection chain, closed-world assumption, LLM guardrails vs. deterministic projection, full architecture diagram, projection rules table, side-effect classification table, trace schema, demo walkthrough, world manifest example, and positioning statement

---

## 2026-04-26 — EPIC 10 / I6: policy trace and audit output (PR claude/safe-skills-epic-s5Y88)

- Updated `wiki/src/safe_mcp_proxy/executor.md` — added world_id/policy_version to __init__; documented list_tools() audit logging; documented execute_skill() trace fields (world_id, policy_version, side_effect, source_provenance)

---

## 2026-04-26 — EPIC 10 / I5: indirect prompt injection demo (PR claude/safe-skills-epic-s5Y88)

- Created `demos/safe_skills/` — full CLI demo: poisoned_document.md, clean_task.md, mock_skills_repo/ (bigquery/email/gke skills), world_manifest.yaml, run_without_proxy.py, run_with_proxy.py, README.md
- Unsafe runner: agent discovers all 3 skills freely, follows hidden instruction, executes email.send (ATTACK SUCCESS)
- Safe runner: proxy projects only bigquery.read_dataset, email.send blocked as capability_not_allowed (ATTACK BLOCKED)
- Both runners use identical inputs — diff is the execution world

---

## 2026-04-26 — EPIC 10 / I4: execution guard for skill-backed capabilities (PR claude/safe-skills-epic-s5Y88)

- Updated `wiki/src/safe_mcp_proxy/executor.md` — added execute_skill, list_tools, _validate_constraints to key symbols; added execute_skill() 7-step guard order section; added capability_projection and compiler to Depends on

---

## 2026-04-26 — EPIC 10 / I3: capability projection engine (PR claude/safe-skills-epic-s5Y88)

- Created `wiki/src/safe_mcp_proxy/capability_projection.md` — new source page: ProjectionContext, ProjectionResult, CapabilityProjectionEngine; evaluation order table; side-effect sets; determinism guarantee; Executor.list_tools() integration
- Updated `wiki/src/safe_mcp_proxy/index.md` — added capability_projection row
- Updated `wiki/index.md` — added capability_projection source page row

---

## 2026-04-26 — EPIC 10 / I2: world manifest skill capability declarations (PR claude/safe-skills-epic-s5Y88)

- Updated `wiki/src/safe_mcp_proxy/compiler.md` — added SkillSourceConfig, SkillCapabilityConfig, parse_skill_sources, parse_skill_capabilities to key symbols; added skill_sources and skill_capabilities to compile_world_manifest() output table; documented skill-backed capability detection rule and validation

---

## 2026-04-26 — EPIC 10 / I1: skill source registry (PR claude/safe-skills-epic-s5Y88)

- Created `wiki/src/safe_mcp_proxy/skill_registry.md` — new source page: SkillSource, ImportedSkill, SkillSourceRegistry; core no-auto-exposure invariant; local vs git source types; compound key scheme; export_manifest / save_manifest
- Updated `wiki/src/safe_mcp_proxy/index.md` — added skill_registry row
- Updated `wiki/index.md` — added skill_registry source page row

---

## 2026-04-25 — Parameterized capability DSL + audit log gitignore (Issue #112)

- Created `wiki/src/safe_mcp_proxy/capability_dsl.md` — new source page: value sources (LiteralSource, ActorInputSource, ContextRefSource), CapabilityDef, parse_capability_definitions(), how _build_scoped_tool() uses them, security invariant (literals always win)
- Updated `wiki/src/safe_mcp_proxy/registry.md` — added _build_scoped_tool entry to key symbols; documented with_mock_tools capability_defs param; added capability_dsl to Depends on
- Updated `wiki/src/safe_mcp_proxy/compiler.md` — added capability_definitions and approval_required to compile_world_manifest() output table; added capability_dsl to Depends on
- Updated `wiki/src/safe_mcp_proxy/main.md` — build_executor() step 3 now shows capability_defs passed to with_mock_tools
- Updated `wiki/world-manifest.md` — added capability_definitions to compiled output table; added new "Parameterized capability definitions" section with YAML syntax, value source table, and allowlist requirement note
- Updated `wiki/architecture.md` — Registry lookup section notes scoped tools are indistinguishable from raw tools at executor level
- Updated `wiki/index.md` — added capability_dsl source page row
- Updated `wiki/src/safe_mcp_proxy/index.md` — added capability_dsl module row
- Updated `wiki/audit-replay.md` — Audit log section notes logs/ is gitignored; documents _seed_if_empty() pattern (seeds/demo.jsonl → logs/audit.jsonl on first API start)

---

## 2026-04-24 — DS7.2: Execution modes (INTERACTIVE and BACKGROUND) (Issue #78)

- Updated `wiki/architecture.md` — pipeline description updated to include `execution_mode` in Provenance stage; PolicyEngine "5 rules" → "6 rules"; Executor dispatch expanded to include ASK/INTERACTIVE and ASK/BACKGROUND paths; added `ExecutionMode` and `ApprovalStore` to component map; added `[[ask-approval]]` and `[[src/safe_mcp_proxy/execution_mode]]` to See also
- Created `safe_mcp_proxy/examples/ask_modes.py` — demo showing INTERACTIVE (ASK + approval token) vs BACKGROUND (immediate DENY fallback) for `send_email`

---

## 2026-04-24 — DS7.1: Document ASK decision and approval workflow (Issue #77)

- Updated `wiki/policy-engine.md` — 5-path → 6-path; added rule 5 (ASK / approval_required); updated summary line; added [[ask-approval]] to See also
- Updated `wiki/audit-replay.md` — added ASK and SIMULATE to `decision` field; documented two-entry audit pattern for INTERACTIVE ASK; documented single-entry DENY pattern for BACKGROUND ASK
- Updated `wiki/absent-deny.md` — added ASK as third distinct outcome (provisional, not terminal); updated See also reference from 5-path to 6-path
- Updated `wiki/index.md` — added [[ask-approval]] concept page row; updated Decision enum description to include ASK; added approval_store and execution_mode source page rows
- Updated `wiki/src/safe_mcp_proxy/decision.md` — "four values" → "five values"; added ASK row; corrected SIMULATE description (implemented, not reserved)
- Updated `wiki/src/safe_mcp_proxy/executor.md` — added approval_store to __init__; added execute_approved and reject_approval methods; added ASK execution paths; added approval_store and execution_mode to Depends on
- Updated `wiki/src/safe_mcp_proxy/index.md` — added approval_store and execution_mode module rows; 5-path → 6-path; added [[ask-approval]] to See also
- Created `wiki/ask-approval.md` — new concept page: what ASK is, how it differs from DENY, trigger, execution modes, lifecycle, API endpoints, audit entries, replay semantics
- Created `wiki/src/safe_mcp_proxy/approval_store.md` — new source page: PendingApproval fields, ApprovalStore methods, status state machine
- Created `wiki/src/safe_mcp_proxy/execution_mode.md` — new source page: INTERACTIVE vs BACKGROUND values, effect on ASK, CLI usage

---

## 2026-04-24 — Publishing infrastructure + Claude Code wiki integration

- Created `mkdocs.yml` — mkdocs-material static site built from `wiki/` directory
- Created `vercel.json` — Vercel build config (`buildCommand: mkdocs build`, `outputDirectory: site`)
- Created `requirements-docs.txt` — doc-only dependencies (`mkdocs`, `mkdocs-material`), separate from runtime
- Created `wiki/publishing.md` — deployment guide (Vercel, GitHub Pages, local preview, wikilinks caveat)
- Updated `wiki/index.md` — added `publishing.md` to Meta Pages table
- Updated `CLAUDE.md` — added `## Wiki` section directing Claude to read relevant pages before and after non-trivial tasks

---

## 2026-04-24 — Initial seed ingest

- Ingested full codebase: `safe_mcp_proxy/`, `api/`, `tests/`, `worlds/`, `seeds/`
- Ingested configuration: `world_manifest.yaml`, `safe_mcp_proxy/config/policy.yaml`, `safe_mcp_proxy/config/worlds/`
- Ingested policies: `safe_mcp_proxy/policies/proxy.rego`
- Created meta pages: `schema.md`, `index.md`, `log.md`
- Created concept pages: `absent-deny.md`, `world-manifest.md`, `policy-engine.md`, `provenance-taint.md`, `descriptor-drift.md`, `audit-replay.md`, `architecture.md`
- Created source mirror: `src/` tree covering all packages and modules
- No contradictions found in this initial pass
- All cross-links verified against created files
