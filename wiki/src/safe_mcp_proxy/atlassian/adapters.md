# `atlassian/adapters.py`

## Role

Adapter registry for the Atlassian Remote MCP Server. Declares every known Jira and Confluence tool as a `ToolAdapter`; provides the `apply_safe_abstraction()` transformer that truncates raw Confluence content.

## Key symbols

| Name | Kind | Description |
|------|------|-------------|
| `ToolAdapter` | frozen dataclass | Per-tool metadata: `name`, `service`, `capability`, `side_effect`, `atomic`, `safe_alias` |
| `ATLASSIAN_TOOLS` | constant | `Dict[str, ToolAdapter]` — full registry of ~22 Jira + Confluence tools |
| `COMPOSITE_TOOLS` | constant | `List[str]` — non-atomic tools suitable for deny-list defaults |
| `apply_safe_abstraction` | function | Applies truncation/abstraction to a `tools/call` response if a `safe_alias` is defined |
| `_truncate_text_blocks` | function | Truncates all text content blocks to `max_chars` characters (default 500) |

## `ToolAdapter` fields

| Field | Type | Values |
|-------|------|--------|
| `service` | str | `"jira"` or `"confluence"` |
| `capability` | str | `jira_read`, `jira_write`, `confluence_read`, `confluence_write` |
| `side_effect` | str | `"read"` or `"write"` |
| `atomic` | bool | False = composite / destructive (deny-list candidates) |
| `safe_alias` | Optional[str] | Name of safe-abstraction variant; None if no abstraction defined |

## Safe abstraction

`confluence_get_page` has `safe_alias="confluence_get_page_summary"`. When `apply_safe_abstraction` is called:
1. All text content blocks are truncated to 500 characters.
2. A `_truncated: true` field is added to truncated blocks.
3. `result._abstraction` is set to `"confluence_get_page_summary"`.

The truncation prevents raw Confluence storage-format content from reaching the LLM, mitigating indirect prompt injection via wiki pages.

## Composite tools (deny-list candidates by default)

- `jira_bulk_create_issues`
- `jira_delete_issue`

## Depends on

Nothing outside the standard library.

## Used by

- [[src/safe_mcp_proxy/atlassian/passthrough]] — `apply_safe_abstraction()` and `ATLASSIAN_TOOLS` lookup
- [[src/safe_mcp_proxy/atlassian/flow]] — `_OUTPUT_LABELS` is derived from tool names in this registry

## See also

- [[src/safe_mcp_proxy/atlassian/filter]] — uses allowlist/denylist; `COMPOSITE_TOOLS` are typical denied_tools
- [[src/safe_mcp_proxy/atlassian/index]] — subpackage overview
