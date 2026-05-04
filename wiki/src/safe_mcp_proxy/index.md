# `safe_mcp_proxy/` package

The core enforcement package. All policy logic, tool registry, provenance tracking, and audit logging live here.

## Modules

| Module | Role |
|--------|------|
| [[src/safe_mcp_proxy/main]] | CLI entrypoint; `build_executor()` assembly function |
| [[src/safe_mcp_proxy/executor]] | Pipeline orchestrator; audit log writer |
| [[src/safe_mcp_proxy/registry]] | Tool definitions and allowlist-filtered dispatch |
| [[src/safe_mcp_proxy/policy_engine]] | Pure Python 6-path decision logic |
| [[src/safe_mcp_proxy/opa_engine]] | OPA/Rego drop-in for `PolicyEngine` |
| [[src/safe_mcp_proxy/provenance]] | `Provenance` dataclass; taint tracking |
| [[src/safe_mcp_proxy/descriptor]] | SHA256 schema normalization and validation |
| [[src/safe_mcp_proxy/compiler]] | World manifest YAML parser |
| [[src/safe_mcp_proxy/decision]] | `Decision` enum |
| [[src/safe_mcp_proxy/simulate]] | Mock external action for tests/demos |
| [[src/safe_mcp_proxy/mcp_server]] | Policy-enforced MCP server — `tools/list` and `tools/call` routing |
| [[src/safe_mcp_proxy/mcp_test_server]] | Minimal upstream MCP server for integration tests |
| [[src/safe_mcp_proxy/mcp_upstream]] | `UpstreamConnector` — MCP client for forwarding ALLOW'd calls |
| [[src/safe_mcp_proxy/trace_store]] | Read-only streaming view of audit JSONL |
| [[src/safe_mcp_proxy/bundle_replay]] | Offline bundle replayer |
| [[src/safe_mcp_proxy/approval_store]] | In-memory approval token store — pending/approved/rejected/executed |
| [[src/safe_mcp_proxy/execution_mode]] | `ExecutionMode` enum: INTERACTIVE vs BACKGROUND |
| [[src/safe_mcp_proxy/capability_dsl]] | Parameterized capability DSL — `LiteralSource`, `ActorInputSource`, `CapabilityDef`, parser |
| [[src/safe_mcp_proxy/skill_registry]] | External skill source registry — import and catalogue skills without auto-exposing them |
| [[src/safe_mcp_proxy/capability_projection]] | Deterministic capability projection engine — `ProjectionContext`, `ProjectionResult`, `CapabilityProjectionEngine` |

## Sub-packages

| Package | Role |
|---------|------|
| [[src/safe_mcp_proxy/config/index]] | `policy.yaml` + per-world YAML manifests |
| [[src/safe_mcp_proxy/examples/index]] | Standalone demo scripts and compatibility wrappers |
| [[src/safe_mcp_proxy/scenarios/index]] | Registered, runnable test scenarios |
| [[src/safe_mcp_proxy/policies/index]] | OPA Rego policy files |
| [[src/safe_mcp_proxy/atlassian/index]] | Atlassian MCP passthrough — policy, filter, flow, adapters, trace reader, CLI |
| [[src/safe_mcp_proxy/integrations/index]] | External LLM runtime adapters (Gemini function-call format) |

## Logs

`safe_mcp_proxy/logs/audit.jsonl` — append-only decision log. See [[audit-replay]].

## See also

- [[absent-deny]] — the core semantic distinction this package enforces
- [[world-manifest]] — the static policy surface consumed by this package
- [[policy-engine]] — the 6-path decision logic at the heart of the package
- [[provenance-taint]] — taint tracking implemented in this package
- [[descriptor-drift]] — schema integrity checking implemented in this package
- [[ask-approval]] — ASK decision lifecycle and approval workflow
- [[audit-replay]] — audit log format and replay semantics
- [[architecture]] — how these modules wire together
