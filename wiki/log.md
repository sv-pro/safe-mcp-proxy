# Wiki Log

Append-only record of ingests, queries, and maintenance operations.

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
