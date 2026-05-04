# `mcp_upstream.py`

## Role

MCP client that forwards ALLOW'd tool calls to an upstream MCP server over stdio. The upstream process is spawned as a subprocess; communication uses the MCP SDK `ClientSession` + `stdio_client` transport.

Only called on the ALLOW path inside `MCPProxyServer._call_tool()` — DENY, ABSENT, and ASK decisions short-circuit before reaching this layer.

## Key symbols

| Name | Kind | Description |
|------|------|-------------|
| `UpstreamConnector` | class | Manages subprocess lifetime and `ClientSession` |
| `UpstreamConnector.__init__(command)` | method | Stores command list; does not spawn yet |
| `UpstreamConnector.connect()` | async method | Spawns subprocess, opens stdio transport, initializes `ClientSession` |
| `UpstreamConnector.call_tool(name, arguments)` | async method | Forwards call; parses first `TextContent` block as JSON; falls back to `{"text": raw}` |
| `UpstreamConnector.disconnect()` | async method | Closes `AsyncExitStack`; safe to call without prior `connect()` |

## Lifecycle

```
UpstreamConnector(cmd)
  → connect()        # spawns subprocess, ClientSession.initialize()
  → call_tool(...)   # one call per tools/call forwarded
  → disconnect()     # aclose() AsyncExitStack
```

The connector is created once per server startup and reused across all ALLOW'd calls.

## Error handling

`call_tool()` raises `RuntimeError` if called before `connect()`. If the upstream returns non-JSON text, it wraps it as `{"text": raw}` rather than raising.

## Depends on

- MCP SDK (`mcp.ClientSession`, `mcp.client.stdio.StdioServerParameters`, `mcp.client.stdio.stdio_client`)

## Used by

- [[src/safe_mcp_proxy/mcp_server]] — ALLOW path in `_call_tool()`
- `tests/test_mcp_server.py` — `TestUpstreamConnector`, `test_allow_with_upstream_uses_upstream_result`
- `demos/integrations/claude_code/demo.py` — upstream forwarding demo

## See also

- [[src/safe_mcp_proxy/mcp_test_server]] — default upstream target in tests and demo
- [[src/safe_mcp_proxy/mcp_server]] — caller; only invokes connector on ALLOW decisions
