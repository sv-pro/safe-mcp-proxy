# `safe_mcp_proxy/atlassian/`

## Role

Passthrough proxy for the Atlassian Remote MCP Server (Jira / Confluence). Enforces a separate five-rule deterministic policy engine before forwarding JSON-RPC requests upstream.

## Modules

| Module | Role |
|--------|------|
| [[src/safe_mcp_proxy/atlassian/passthrough]] | `MCPPassthrough` — forward + policy gate + safe abstraction + flow tagging |
| [[src/safe_mcp_proxy/atlassian/policy]] | `ManifestPolicyEngine` — five-rule decision engine (ABSENT / DENY / ALLOW) |
| [[src/safe_mcp_proxy/atlassian/filter]] | `CapabilityFilter` — allowlist/denylist composition for `tools/list` |
| [[src/safe_mcp_proxy/atlassian/flow]] | `FlowContext`, `DataFlowRule` — session-level data-label tracking |
| [[src/safe_mcp_proxy/atlassian/adapters]] | `ToolAdapter`, `ATLASSIAN_TOOLS` — full Atlassian tool registry + safe abstraction transformer |
| [[src/safe_mcp_proxy/atlassian/config]] | `AtlassianProxyConfig` — runtime config (mode, URLs, allowed/denied tools, manifest path) |
| [[src/safe_mcp_proxy/atlassian/trace_reader]] | `AtlassianTraceReader`, `TraceEntry` — read-only JSONL audit log for Atlassian requests |
| [[src/safe_mcp_proxy/atlassian/cli]] | CLI inspector for Atlassian trace logs (`list`, `stats`, `trace` commands) |

## Pipeline (per `tools/call`)

```
Incoming JSON-RPC request
  ↓
Policy gate   — ManifestPolicyEngine.evaluate() → ABSENT / DENY / ALLOW
  ↓ (ALLOW only)
Forward       — HTTP POST to upstream, or stub if upstream not configured
  ↓
Safe abstraction  — confluence_get_page → title + 500-char summary
  ↓
Flow tagging  — FlowContext.tag_output() labels confluence_raw / confluence_summary
  ↓
Response returned (with optional debug flow state)
```

`tools/list` responses pass through `CapabilityFilter` to hide denied/absent tools.

## World manifest

`manifests/atlassian_mvp.yaml` — demonstrates:
- `arg_rules` (argument validation)
- Safe abstractions (Confluence page truncation)
- Data-flow rules blocking raw Confluence → Jira write chains

## See also

- [[src/safe_mcp_proxy/atlassian/passthrough]] — full pipeline orchestrator
- [[src/safe_mcp_proxy/atlassian/policy]] — five-rule engine detail
- [[absent-deny]] — ABSENT / DENY semantics used by this subpackage
- [[provenance-taint]] — `TAINTED_CHANNELS` from `provenance.py` drives taint detection
- [[audit-replay]] — `AtlassianTraceReader` provides the same read pattern as `TraceStore`
