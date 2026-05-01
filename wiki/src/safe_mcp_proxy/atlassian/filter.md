# `atlassian/filter.py`

## Role

`CapabilityFilter` — applies allowlist + denylist to a `tools/list` JSON-RPC response, implementing the ABSENT principle for the Atlassian path. Tools not visible to this world are silently omitted.

## Key symbols

| Name | Kind | Description |
|------|------|-------------|
| `CapabilityFilter` | class | Stateless filter; constructed with `allowed_tools` and `denied_tools` sets |
| `CapabilityFilter.filter_tools` | method | Takes `list[dict]`; returns only tools visible in this world |
| `CapabilityFilter.apply_to_list_response` | method | Deep-copies a `tools/list` response and replaces `result.tools` with the filtered list |

## Semantics

- A tool in `denied_tools` is always hidden (composite / unsafe tools).
- If `allowed_tools` is non-empty: only tools in the allowlist pass through.
- If `allowed_tools` is empty: all tools pass through (passthrough mode); only `denied_tools` are removed.

## Depends on

Nothing outside the standard library.

## Used by

- [[src/safe_mcp_proxy/atlassian/config]] — `AtlassianProxyConfig.capability_filter()` builds one
- [[src/safe_mcp_proxy/atlassian/passthrough]] — applied to `tools/list` responses

## See also

- [[absent-deny]] — hidden tools implement the ABSENT principle
- [[src/safe_mcp_proxy/atlassian/index]] — subpackage overview
