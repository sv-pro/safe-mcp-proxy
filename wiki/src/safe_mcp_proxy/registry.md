# `registry.py`

## Role

Holds tool definitions and enforces the allowlist boundary. The only source of tool handlers, schemas, and descriptor hashes.

## Key symbols

| Name | Kind | Description |
|------|------|-------------|
| `Tool` | dataclass | A single tool record |
| `Tool.name` | field | Tool identifier string |
| `Tool.capability` | field | Capability key (maps to `capability_map` in manifest) |
| `Tool.schema` | field | JSON Schema dict — hashed at registration time |
| `Tool.descriptor_hash` | field | SHA256 of `schema` at registration — used for drift detection |
| `Tool.side_effect_type` | field | `"read"`, `"internal"`, or `"external"` |
| `Tool.handler` | field | `Callable[[dict], dict]` — the tool's implementation |
| `ToolRegistry` | class | Manages upstream tools and allowlist-filtered view |
| `ToolRegistry.with_mock_tools` | classmethod | Factory: creates 4 mock tools + any scoped tools from `capability_defs` |
| `ToolRegistry.get_tool` | method | Returns `Tool` if in allowlist, else `None` |
| `ToolRegistry.execute_tool` | method | Calls `tool.handler(payload)`; raises `KeyError` if not exposed |
| `_build_scoped_tool` | function | Builds a synthetic `Tool` from a `CapabilityDef` with literal injection |

## Mock tools (from `with_mock_tools()`)

| Tool | Capability | Side-effect type |
|------|-----------|-----------------|
| `read_file` | `read_file` | `read` |
| `list_repo` | `list_repo` | `internal` |
| `send_email` | `send_email` | `external` |
| `dangerous_exec` | `dangerous_exec` | `external` |

`descriptor_hash` is computed via `compute_descriptor_hash(schema)` at registration time.

`with_mock_tools(allowlist, capability_defs=None)` accepts an optional `capability_defs` dict. For each `CapabilityDef`, `_build_scoped_tool()` creates a synthetic `Tool` backed by the matching base tool handler with literal args injected and actor-visible schema restricted to `actor_input` params only. Scoped tools are appended to the tool list before the allowlist filter is applied.

## Two tool dicts

- `_all_tools` — all upstream tools (used internally)
- `_exposed_tools` — only tools in the allowlist (used by `get_tool()` and `execute_tool()`)

A tool in `_all_tools` but not in `_exposed_tools` is invisible to the executor — it results in `ABSENT`.

## Depends on

- [[src/safe_mcp_proxy/descriptor]] — `compute_descriptor_hash()`
- [[src/safe_mcp_proxy/capability_dsl]] — `CapabilityDef` and source types consumed by `_build_scoped_tool()`

## Used by

- [[src/safe_mcp_proxy/executor]] — `get_tool()`, `execute_tool()`
- [[src/safe_mcp_proxy/main]] — `ToolRegistry.with_mock_tools(allowlist)`

## See also

- [[absent-deny]] — `get_tool()` returning `None` is the ABSENT trigger
- [[descriptor-drift]] — `descriptor_hash` is pinned here at registration
- [[world-manifest]] — `allowlist` that controls `_exposed_tools` comes from the manifest
- [[policy-engine]] — allowlist fed to `PolicyEngine` comes from the same manifest source
- [[architecture]] — ToolRegistry is stage 2 (lookup) in the fixed pipeline
