# `safe_mcp_proxy/` package

The core enforcement package. All policy logic, tool registry, provenance tracking, and audit logging live here.

## Modules

| Module | Role |
|--------|------|
| [[src/safe_mcp_proxy/main]] | CLI entrypoint; `build_executor()` assembly function |
| [[src/safe_mcp_proxy/executor]] | Pipeline orchestrator; audit log writer |
| [[src/safe_mcp_proxy/registry]] | Tool definitions and allowlist-filtered dispatch |
| [[src/safe_mcp_proxy/policy_engine]] | Pure Python 5-path decision logic |
| [[src/safe_mcp_proxy/opa_engine]] | OPA/Rego drop-in for `PolicyEngine` |
| [[src/safe_mcp_proxy/provenance]] | `Provenance` dataclass; taint tracking |
| [[src/safe_mcp_proxy/descriptor]] | SHA256 schema normalization and validation |
| [[src/safe_mcp_proxy/compiler]] | World manifest YAML parser |
| [[src/safe_mcp_proxy/decision]] | `Decision` enum |
| [[src/safe_mcp_proxy/simulate]] | Mock external action for tests/demos |
| [[src/safe_mcp_proxy/trace_store]] | Read-only streaming view of audit JSONL |
| [[src/safe_mcp_proxy/bundle_replay]] | Offline bundle replayer |

## Sub-packages

| Package | Role |
|---------|------|
| [[src/safe_mcp_proxy/config/index]] | `policy.yaml` + per-world YAML manifests |
| [[src/safe_mcp_proxy/examples/index]] | Standalone demo scripts |
| [[src/safe_mcp_proxy/scenarios/index]] | Registered, runnable test scenarios |
| [[src/safe_mcp_proxy/policies/index]] | OPA Rego policy files |

## Logs

`safe_mcp_proxy/logs/audit.jsonl` — append-only decision log. See [[audit-replay]].

## See also

- [[architecture]] — how these modules wire together
