# `integrations/gemini_adapter.py`

## Role

Stateless adapter that converts a Gemini `functionCall` JSON envelope into a normalized `ToolCall` dataclass and formats results back into the Gemini `functionResponse` envelope. No policy evaluation or I/O.

## Key symbols

| Name | Kind | Description |
|------|------|-------------|
| `GeminiAdapterError` | exception | Raised when a required field is missing or malformed; carries `.field` attribute |
| `ToolCall` | dataclass | Normalized tool request: `tool_name`, `arguments`, `session_id`, `agent_id`, `metadata`, `raw_request` |
| `GeminiAdapter` | class | Stateless adapter; all methods are classmethods |
| `GeminiAdapter.parse` | classmethod | `request: dict → ToolCall`; raises `GeminiAdapterError` on bad input |
| `GeminiAdapter.format_response` | classmethod | `(tool_name, result) → {"functionResponse": {"name": ..., "response": ...}}` |

## `parse()` behavior

Input shape expected:
```json
{
  "functionCall": {"name": "<tool_name>", "args": {...}},
  "metadata": {"session_id": "...", "agent_id": "..."}
}
```

- `functionCall` is required; missing → `GeminiAdapterError("functionCall")`
- `functionCall.name` is required; empty → `GeminiAdapterError("name")`
- `functionCall.args` defaults to `{}` if absent or null
- `metadata` is optional; `session_id` and `agent_id` are extracted if present

## Depends on

Nothing outside the standard library.

## Used by

Not yet wired into the executor; intended for use when a Gemini-hosted agent routes tool calls through the proxy. Tests in `tests/test_gemini_adapter.py`.

## See also

- [[src/safe_mcp_proxy/integrations/index]] — integrations subpackage overview
- [[src/safe_mcp_proxy/executor]] — downstream consumer of normalized tool calls
