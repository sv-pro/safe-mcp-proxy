# `demos/integrations/`

Runtime-specific demos for external agent and SaaS integration surfaces.

| Path | Demonstrates | Command |
|------|--------------|---------|
| `claude_code/demo.py` | MCP `tools/list` world scoping, taint blocking, absent tools, upstream forwarding | `python -m demos.integrations.claude_code.demo` |
| `gemini/demo.py` | Gemini `functionCall` baseline vs protected execution through `GeminiProxy` | `python -m demos.integrations.gemini.demo` |
| `atlassian/demo.py` | Confluence read followed by Jira write with raw-data-flow denial | `python -m demos.integrations.atlassian.demo` |

The Claude Code and Gemini demos exercise the core executor. The Atlassian demo
uses the Atlassian passthrough policy layer in `safe_mcp_proxy/atlassian/`.

See also:

- [[src/safe_mcp_proxy/mcp_server]]
- [[src/safe_mcp_proxy/integrations/index]]
- [[src/safe_mcp_proxy/atlassian/index]]
