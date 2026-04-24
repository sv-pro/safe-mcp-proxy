# Wiki Schema

This document defines conventions for the safe-mcp-proxy wiki. It is co-evolved by humans and LLMs as the project grows.

## Purpose

This wiki is a persistent, AI-maintained knowledge base following the LLM Wiki pattern (Andrej Karpathy, 2025). It accumulates synthesized knowledge about the project incrementally — rather than regenerating answers from raw sources on each query.

Three layers:
- **Raw sources** (immutable): source code, YAML configs, tests — never modified by the wiki
- **The wiki** (mutable): this directory — markdown files created and maintained by AI
- **This schema** (configuration): defines structure and update conventions

## Page Types

### Concept page
Documents a core idea, design principle, or security mechanism.

```
# <Concept Name>

## What it is
One-paragraph definition.

## Why it exists
The threat or problem it addresses.

## How it works
Mechanism / implementation details.

## See also
- [[related-page]]
```

### Source page
Documents a Python module or package. Lives under `src/` mirroring the package hierarchy.

```
# `<module_name.py>` / `<package/>`

## Role
One-line responsibility.

## Key symbols
| Name | Kind | Description |
|------|------|-------------|
| ... | class/function/constant | ... |

## Depends on
- [[other-module]]

## Used by
- [[other-module]]
```

### Meta page
`index.md`, `log.md`, `schema.md` — not content pages, never linked as `[[...]]`.

## Cross-linking

Use `[[page-name]]` (filename without `.md`) to reference other wiki pages. All references must point to real files. Do not create dangling links.

Examples:
- `[[absent-deny]]` → `wiki/absent-deny.md`
- `[[src/safe_mcp_proxy/executor]]` → `wiki/src/safe_mcp_proxy/executor.md`

## Update Operations

**Ingest**: A new source (issue, ADR, code change) is processed. The LLM reads it, updates affected pages, creates new pages if needed, appends to `log.md`.

**Query**: A question is answered by reading relevant wiki pages. The answer can itself become a new page.

**Lint**: Periodic health check — find contradictions, stale claims, orphaned pages, missing cross-links.

## Naming Conventions

- Concept pages: `kebab-case.md` at wiki root
- Source pages: `wiki/src/<package>/<module>.md`, mirroring the repo hierarchy
- Package overview: `wiki/src/<package>/index.md`
- All filenames lowercase

## Accuracy Requirement

Every claim in this wiki must be grounded in the actual source code, configuration files, or documentation in this repository. Do not invent APIs, behavior, or design rationale that cannot be verified in the codebase.
