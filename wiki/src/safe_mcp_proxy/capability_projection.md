# `capability_projection.py`

## Role

Deterministic capability projection engine — filters `skill_capabilities` from the world manifest into the subset visible to an agent for a given execution context.

## Key symbols

| Name | Kind | Description |
|------|------|-------------|
| `ProjectionContext` | dataclass | Execution context: identity, workflow_id, mode, trust_context, approved_capabilities |
| `ProjectionResult` | dataclass | Output: `visible` list of `SkillCapabilityConfig`; `hidden` list of `(name, reason)` pairs |
| `CapabilityProjectionEngine` | class | Stateless engine; `project(skill_capabilities, context) → ProjectionResult` |
| `_is_readonly_workflow` | function | Convention: workflow_id starting with `read_only`/`read-only` or ending with `_ro` |

## Evaluation order

Rules are checked in fixed priority order. First match wins:

| # | Condition | Reason code |
|---|-----------|-------------|
| 1 | `allowed == False` | `capability_not_allowed` |
| 2 | background mode + side_effect in `_BACKGROUND_BLOCKED` | `side_effect_restricted_in_background` |
| 3 | read-only workflow + side_effect in `_WRITE_SIDE_EFFECTS` | `side_effect_not_allowed_in_workflow` |
| 4 | `requires_approval == True` and capability not in `approved_capabilities` | `approval_required` |
| 5 | (none of the above) | visible |

## Side-effect sets

| Set | Members | Applies to |
|-----|---------|-----------|
| `_WRITE_SIDE_EFFECTS` | `write`, `external_communication`, `deployment` | Hidden in read-only workflows |
| `_BACKGROUND_BLOCKED` | `_WRITE_SIDE_EFFECTS` + `bounded_compute` | Hidden in BACKGROUND mode |

Background mode is strictly more restrictive than interactive mode.

## Determinism guarantee

`project()` is a pure function — no I/O, no randomness. Same `skill_capabilities` dict + same `ProjectionContext` always produce identical `ProjectionResult`.

## Integration with Executor

`Executor` accepts optional `projection_engine` and `skill_capabilities` constructor params. `Executor.list_tools(context)` delegates to `projection_engine.project(skill_capabilities, context)`. When no projection engine is configured, `list_tools()` returns empty `ProjectionResult`.

## Depends on

- [[src/safe_mcp_proxy/compiler]] — `SkillCapabilityConfig`
- [[src/safe_mcp_proxy/execution_mode]] — `ExecutionMode`

## Used by

- [[src/safe_mcp_proxy/executor]] — `list_tools()` method
- EPIC 10 demo: `demos/safe_skills/`

## See also

- [[absent-deny]] — ABSENT semantic: capabilities outside the projection simply do not exist
- [[world-manifest]] — `skill_capabilities` originates from the compiled manifest
- [[src/safe_mcp_proxy/skill_registry]] — skill import (separate concern from projection)
