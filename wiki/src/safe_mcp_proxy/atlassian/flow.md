# `atlassian/flow.py`

## Role

Data-flow control (provenance lite) for the Atlassian MCP path. `FlowContext` tracks which data labels are active in a session; `DataFlowRule` encodes which labels block which tools.

## Key symbols

| Name | Kind | Description |
|------|------|-------------|
| `LABEL_CONFLUENCE_RAW` | constant | `"confluence_raw"` — label for un-abstracted Confluence page content |
| `LABEL_CONFLUENCE_SUMMARY` | constant | `"confluence_summary"` — label for safe-abstracted Confluence content |
| `FlowContext` | class | Mutable session-level set of active data labels |
| `FlowContext.tag_output` | method | Called after a successful tool call; adds the appropriate label |
| `FlowContext.has_label` | method | Returns True if label is active |
| `FlowContext.active_labels` | method | Returns a copy of the current label set |
| `FlowContext.clear` | method | Resets all labels |
| `FlowContext.as_dict` | method | Serializes for debug output |
| `DataFlowRule` | dataclass | `(if_label, deny_for: list[str], rule: str)` |
| `parse_data_flow_rules` | function | Converts raw manifest YAML list → `list[DataFlowRule]` |

## Label assignment

| Tool | Was abstracted | Label added |
|------|---------------|-------------|
| `confluence_get_page` | No | `confluence_raw` |
| `confluence_get_page` | Yes | `confluence_summary` |
| Any other tool | — | (no label added) |

## Flow rule enforcement

Rules are evaluated in `ManifestPolicyEngine.evaluate()` (rule 3):
> If `FlowContext.has_label(dfr.if_label)` and `tool_name in dfr.deny_for` → DENY.

Example manifest rule that blocks raw Confluence content from flowing into Jira writes:
```yaml
data_flow_rules:
  - if_label: confluence_raw
    deny_for: [jira_create_issue, jira_update_issue]
    rule: raw_confluence_blocks_jira_write
```

## Depends on

Nothing outside the standard library.

## Used by

- [[src/safe_mcp_proxy/atlassian/policy]] — `ManifestPolicyEngine` evaluates `DataFlowRule` entries
- [[src/safe_mcp_proxy/atlassian/passthrough]] — `MCPPassthrough` holds and updates `FlowContext`

## See also

- [[provenance-taint]] — the core pipeline's taint mechanism; this is an analogous per-session label tracker
- [[src/safe_mcp_proxy/atlassian/index]] — subpackage overview
