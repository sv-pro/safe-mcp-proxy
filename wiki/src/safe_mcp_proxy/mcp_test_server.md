# `mcp_test_server.py`

## Role

Minimal upstream MCP server used as a test backend. Exposes four tools that mirror the registry mock tools, with stub responses. Blocked tools (`send_email`, `dangerous_exec`) are intentionally included so the proxy's DENY path can be exercised in integration tests without requiring a real external service.

Run standalone: `python -m safe_mcp_proxy.mcp_test_server`

## Tools exposed

| Tool | Side effect | Stub response |
|------|-------------|---------------|
| `read_file` | read | `{"content": "<contents of {path}>", "path": path}` |
| `list_repo` | internal | `{"files": ["README.md", "safe_mcp_proxy/", "tests/"]}` |
| `send_email` | external | `{"sent": true, "to": to}` |
| `dangerous_exec` | external | `{"stdout": "<output of: {cmd}>", "exit_code": 0}` |

`send_email` and `dangerous_exec` will never be reached through the proxy in a correctly configured world — the policy layer blocks them before forwarding.

## Key symbols

| Name | Kind | Description |
|------|------|-------------|
| `_server` | `mcp.server.Server` | Module-level MCP SDK server instance |
| `handle_list_tools()` | handler | Returns `_TOOLS` list |
| `handle_call_tool(name, arguments)` | handler | Dispatches to per-tool stub |

## Depends on

- MCP SDK (`mcp.server.Server`, `mcp.server.stdio.stdio_server`, `mcp.types`)

## Used by

- [[src/safe_mcp_proxy/mcp_upstream]] — spawned as subprocess by `UpstreamConnector`
- `tests/test_mcp_server.py` — `TestMCPTestServer` and `TestUpstreamConnector`
- [[src/safe_mcp_proxy/examples/claude_code_demo]] — upstream forwarding demo

## See also

- [[src/safe_mcp_proxy/mcp_server]] — proxy server that sits in front of this upstream
- [[src/safe_mcp_proxy/mcp_upstream]] — client that connects to this server
