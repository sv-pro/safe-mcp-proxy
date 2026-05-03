# `mcp_server.py`

## Role

Policy-enforced MCP server. Every `tools/list` and `tools/call` request from an MCP client (Claude Code, VS Code) is routed through the executor's policy pipeline before being forwarded to an optional upstream MCP server.

Entry point: `python -m safe_mcp_proxy.mcp_server`

## Key symbols

| Name | Kind | Description |
|------|------|-------------|
| `MCPProxyServer` | class | Wraps `Executor` + optional `UpstreamConnector`; builds the MCP SDK `Server` instance |
| `MCPProxyServer._list_tools()` | method | Returns world-filtered tool list as `list[mcp.types.Tool]`; directly testable |
| `MCPProxyServer._call_tool(name, arguments)` | async method | Runs executor policy; maps decision to MCP response or `McpError` |
| `MCPProxyServer.run_stdio()` | async method | Enters stdio transport loop; called by CLI entry point |
| `main()` | function | CLI entry point; parses args, wires executor + upstream, calls `asyncio.run()` |

## Decision mapping

| Executor decision | MCP outcome |
|-------------------|-------------|
| `ALLOW` | Forward to upstream (if present) or return mock result as `TextContent` |
| `DENY` | `McpError(INTERNAL_ERROR, "DENY: <rule>")` |
| `ABSENT` | `McpError(INTERNAL_ERROR, "ABSENT: <rule>")` |
| `ASK` (INTERACTIVE) | `McpError` with approval token in message |
| `ASK` (BACKGROUND) | Collapses to DENY inside executor before reaching server |

## CLI args

| Arg | Default | Description |
|-----|---------|-------------|
| `--world WORLD_ID` | `None` (uses `world_manifest.yaml`) | World manifest to load |
| `--upstream CMD...` | `None` | Command to spawn upstream MCP server |
| `--mode interactive\|background` | `interactive` | Controls ASK behaviour |

## Provenance

All calls arrive with `Provenance.from_source("cli")` — the transport boundary is trusted. Taint is only injected by upstream tool outputs if those are re-fed into the payload.

## Depends on

- [[src/safe_mcp_proxy/executor]] — `execute()` call on the `tools/call` path
- [[src/safe_mcp_proxy/registry]] — `list_exposed()` on the `tools/list` path
- [[src/safe_mcp_proxy/mcp_upstream]] — `call_tool()` on the ALLOW path
- [[src/safe_mcp_proxy/provenance]] — `Provenance.from_source("cli")`
- [[src/safe_mcp_proxy/execution_mode]] — `ExecutionMode.INTERACTIVE / BACKGROUND`
- [[src/safe_mcp_proxy/main]] — `build_executor()` for CLI wiring

## Used by

- Claude Code — via `.mcp.json` project config (auto-discovered)
- [[src/safe_mcp_proxy/examples/claude_code_demo]] — integration demo
- `tests/test_mcp_server.py` — unit and integration tests

## See also

- [[architecture]] — where MCP server fits in the pipeline
- [[absent-deny]] — ABSENT vs DENY semantics exposed as MCP errors
- [[ask-approval]] — ASK token lifecycle in INTERACTIVE mode
- [[world-manifest]] — world configuration loaded at startup
