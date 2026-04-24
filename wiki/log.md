# Wiki Log

Append-only record of ingests, queries, and maintenance operations.

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
