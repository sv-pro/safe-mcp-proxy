from __future__ import annotations

from typing import Any, Dict, List, Set


class CapabilityFilter:
    """Filter a tools/list result against an allowlist and deny-list.

    Semantics follow the ABSENT principle:
    - A tool not in the allowlist does not exist in this world.
    - A tool in the deny-list is explicitly hidden (composite / unsafe).
    - If allowed_tools is empty the filter is in passthrough mode (all tools
      pass through, only deny-list is enforced).
    """

    def __init__(
        self,
        allowed_tools: Set[str],
        denied_tools: Set[str],
    ) -> None:
        self._allowed = allowed_tools
        self._denied = denied_tools

    # ------------------------------------------------------------------

    def filter_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Return only the tools that are visible in this world."""
        result = []
        for tool in tools:
            name = tool.get("name", "")
            if name in self._denied:
                continue
            if self._allowed and name not in self._allowed:
                continue
            result.append(tool)
        return result

    def apply_to_list_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Return a copy of a tools/list JSON-RPC response with tools filtered."""
        result = dict(response)
        inner = dict(result.get("result", {}))
        inner["tools"] = self.filter_tools(inner.get("tools", []))
        result["result"] = inner
        return result
