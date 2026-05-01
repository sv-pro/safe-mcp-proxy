# `atlassian/passthrough.py`

## Role

`MCPPassthrough` — orchestrates the full Atlassian MCP pipeline: policy gate → HTTP forward → safe abstraction → flow tagging → optional debug output. One public method: `forward(request)`.

## Key symbols

| Name | Kind | Description |
|------|------|-------------|
| `MCPPassthrough` | class | Stateful pipeline orchestrator. Holds config, log path, policy, and flow context. |
| `MCPPassthrough.__init__` | method | Takes `config`, optional `log_path`, optional `policy`, optional `flow_context` |
| `MCPPassthrough.forward` | method | Main entry point — routes any JSON-RPC method through the full pipeline |
| `MCPPassthrough._http_forward` | method | HTTP POST to `config.upstream_url` via `urllib.request` |
| `MCPPassthrough._stub_response` | method | Returns static stub when upstream is not configured |
| `MCPPassthrough._log` | method | Appends JSON entry to JSONL log file |
| `MCPPassthrough._log_decision` | method | Appends decision entry (tool, decision, rule, tainted, flow_labels, trace_id) |
| `_blocked_response` | function | Builds JSON-RPC error response for ABSENT/DENY decisions |
| `_error_response` | function | Builds JSON-RPC error response for upstream failures |

## `forward()` logic

1. Log incoming request with a fresh `trace_id`.
2. **Policy gate** (only for `tools/call`): call `ManifestPolicyEngine.evaluate()`; if not ALLOW, return `_blocked_response` immediately.
3. **Forward**: HTTP POST to upstream, or call `_stub_response` if unconfigured.
4. **Safe abstraction** (only for `tools/call`): `apply_safe_abstraction()` truncates Confluence content.
5. **Flow tagging** (only for `tools/call`): `FlowContext.tag_output()` labels the output.
6. **Capability filter** (only for `tools/list`): `CapabilityFilter.apply_to_list_response()`.
7. **Debug mode**: if `config.debug`, inject `_debug.flow_context` into the result.
8. Log response and return.

## Stub responses

When `upstream_url` is empty or `mode != "proxy"`, stubs are returned:
- `tools/list` → `{"tools": []}`
- `tools/call` → error result `"Upstream not configured"`
- `initialize` → server info with protocol version `2024-11-05`

## Depends on

- [[src/safe_mcp_proxy/atlassian/config]] — `AtlassianProxyConfig`
- [[src/safe_mcp_proxy/atlassian/policy]] — `ManifestPolicyEngine`, `PolicyDecision`
- [[src/safe_mcp_proxy/atlassian/flow]] — `FlowContext`
- [[src/safe_mcp_proxy/atlassian/adapters]] — `apply_safe_abstraction`, `ATLASSIAN_TOOLS`
- [[src/safe_mcp_proxy/provenance]] — `TAINTED_CHANNELS`

## Used by

- `api/main.py` — `POST /atlassian/mcp` endpoint
- [[src/safe_mcp_proxy/atlassian/cli]] — CLI entrypoint for standalone inspection

## See also

- [[src/safe_mcp_proxy/atlassian/index]] — subpackage overview and pipeline diagram
- [[absent-deny]] — blocked responses encode ABSENT vs DENY semantics
