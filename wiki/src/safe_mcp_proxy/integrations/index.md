# `safe_mcp_proxy/integrations/`

## Role

Adapter layer for external LLM runtimes. Converts provider-specific function-call formats into the internal `ToolCall` representation used by the proxy pipeline.

## Modules

| Module | Role |
|--------|------|
| [[src/safe_mcp_proxy/integrations/gemini_adapter]] | `GeminiAdapter` — stateless parser for Gemini `functionCall` JSON |

## Design principle

Adapters are stateless and do not execute or validate tool calls against policy. They only normalize the wire format so that any upstream caller can feed requests into the executor without being aware of provider-specific JSON shapes.

## See also

- [[src/safe_mcp_proxy/executor]] — the executor receives normalized `ToolCall` objects
- [[src/safe_mcp_proxy/index]] — parent package overview
