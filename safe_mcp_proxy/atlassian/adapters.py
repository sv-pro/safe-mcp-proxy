"""Adapter registry for Atlassian Remote MCP Server tool names.

Tool names are sourced from the Atlassian Remote MCP Server
(mcp.atlassian.com / atlassian-labs/mcp-atlassian).

Each ToolAdapter describes:
- service:      "jira" | "confluence"
- capability:   logical capability group (maps to world_manifest capabilities)
- side_effect:  "read" | "write"
- atomic:       False = composite tool (multiple side effects in one call)
- safe_alias:   name of a safe-abstraction variant, if one is defined
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ToolAdapter:
    name: str
    service: str
    capability: str
    side_effect: str     # "read" | "write"
    atomic: bool
    safe_alias: Optional[str] = None


# ---------------------------------------------------------------------------
# Atlassian Remote MCP Server — full tool registry
# ---------------------------------------------------------------------------

ATLASSIAN_TOOLS: Dict[str, ToolAdapter] = {
    # ------------------------------------------------------------------
    # Jira — read
    # ------------------------------------------------------------------
    "jira_get_issue": ToolAdapter(
        "jira_get_issue", "jira", "jira_read", "read", atomic=True
    ),
    "jira_search_issues_using_jql": ToolAdapter(
        "jira_search_issues_using_jql", "jira", "jira_read", "read", atomic=True
    ),
    "jira_get_transitions": ToolAdapter(
        "jira_get_transitions", "jira", "jira_read", "read", atomic=True
    ),
    "jira_get_project": ToolAdapter(
        "jira_get_project", "jira", "jira_read", "read", atomic=True
    ),
    "jira_list_projects": ToolAdapter(
        "jira_list_projects", "jira", "jira_read", "read", atomic=True
    ),
    "jira_get_board": ToolAdapter(
        "jira_get_board", "jira", "jira_read", "read", atomic=True
    ),
    "jira_get_sprint": ToolAdapter(
        "jira_get_sprint", "jira", "jira_read", "read", atomic=True
    ),
    "jira_get_user": ToolAdapter(
        "jira_get_user", "jira", "jira_read", "read", atomic=True
    ),
    # ------------------------------------------------------------------
    # Jira — write (atomic)
    # ------------------------------------------------------------------
    "jira_create_issue": ToolAdapter(
        "jira_create_issue", "jira", "jira_write", "write", atomic=True
    ),
    "jira_update_issue": ToolAdapter(
        "jira_update_issue", "jira", "jira_write", "write", atomic=True
    ),
    "jira_transition_issue": ToolAdapter(
        "jira_transition_issue", "jira", "jira_write", "write", atomic=True
    ),
    "jira_add_comment": ToolAdapter(
        "jira_add_comment", "jira", "jira_write", "write", atomic=True
    ),
    "jira_assign_issue": ToolAdapter(
        "jira_assign_issue", "jira", "jira_write", "write", atomic=True
    ),
    # ------------------------------------------------------------------
    # Jira — composite / destructive (deny-list candidates)
    # ------------------------------------------------------------------
    "jira_bulk_create_issues": ToolAdapter(
        "jira_bulk_create_issues", "jira", "jira_write", "write", atomic=False
    ),
    "jira_delete_issue": ToolAdapter(
        "jira_delete_issue", "jira", "jira_write", "write", atomic=False
    ),
    # ------------------------------------------------------------------
    # Confluence — read
    # safe_alias: confluence_get_page has a safe abstraction that returns
    # title + summary only (not raw storage-format content)
    # ------------------------------------------------------------------
    "confluence_get_page": ToolAdapter(
        "confluence_get_page", "confluence", "confluence_read", "read",
        atomic=True, safe_alias="confluence_get_page_summary",
    ),
    "confluence_search_pages": ToolAdapter(
        "confluence_search_pages", "confluence", "confluence_read", "read", atomic=True
    ),
    "confluence_get_space": ToolAdapter(
        "confluence_get_space", "confluence", "confluence_read", "read", atomic=True
    ),
    "confluence_list_spaces": ToolAdapter(
        "confluence_list_spaces", "confluence", "confluence_read", "read", atomic=True
    ),
    # ------------------------------------------------------------------
    # Confluence — write
    # ------------------------------------------------------------------
    "confluence_create_page": ToolAdapter(
        "confluence_create_page", "confluence", "confluence_write", "write", atomic=True
    ),
    "confluence_update_page": ToolAdapter(
        "confluence_update_page", "confluence", "confluence_write", "write", atomic=True
    ),
    "confluence_add_comment": ToolAdapter(
        "confluence_add_comment", "confluence", "confluence_write", "write", atomic=True
    ),
}

# Convenience: non-atomic tools that should appear on deny-lists by default.
COMPOSITE_TOOLS: List[str] = [
    name for name, a in ATLASSIAN_TOOLS.items() if not a.atomic
]


# ---------------------------------------------------------------------------
# Safe-abstraction response transformer
# ---------------------------------------------------------------------------

def apply_safe_abstraction(tool_name: str, response: Dict[str, Any]) -> Dict[str, Any]:
    """Apply a safe abstraction to a tools/call response if one is defined.

    Currently: confluence_get_page → strip raw storage body, keep
    title + summary (first 500 chars of plain text) only.
    """
    adapter = ATLASSIAN_TOOLS.get(tool_name)
    if adapter is None or adapter.safe_alias is None:
        return response

    result = dict(response)
    inner = dict(result.get("result", {}))
    content: List[Dict[str, Any]] = list(inner.get("content", []))
    inner["content"] = _truncate_text_blocks(content, max_chars=500)
    inner["_abstraction"] = adapter.safe_alias
    result["result"] = inner
    return result


def _truncate_text_blocks(
    content: List[Dict[str, Any]], max_chars: int
) -> List[Dict[str, Any]]:
    """Truncate all text content blocks to max_chars characters."""
    out = []
    for block in content:
        if block.get("type") == "text":
            text = block.get("text", "")
            block = dict(block)
            if len(text) > max_chars:
                block["text"] = text[:max_chars] + "…"
                block["_truncated"] = True
        out.append(block)
    return out
