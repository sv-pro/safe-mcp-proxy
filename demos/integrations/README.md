# Integration Demos

These demos prove the same policy model across external agent/runtime shapes.

| Demo | What it does | Value | Command |
|---|---|---|---|
| `claude_code/demo.py` | Exercises MCP `tools/list`, taint blocking, absent tools, and upstream forwarding. | Shows safe-mcp-proxy operating as a real MCP server boundary. | `python -m demos.integrations.claude_code.demo` |
| `gemini/demo.py` | Runs the same Gemini-style function call through baseline and protected execution. | Shows `send_email` becoming ontologically absent in the `gemini_demo` world. | `python -m demos.integrations.gemini.demo` |
| `atlassian/demo.py` | Simulates Confluence read followed by Jira write with and without the proxy. | Shows data-flow policy blocking raw Confluence content from leaking into Jira. | `python -m demos.integrations.atlassian.demo` |
