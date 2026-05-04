from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from safe_mcp_proxy.mcp_upstream import UpstreamConnector
from safe_mcp_proxy.policy import JiraPolicy


@dataclass
class Decision:
    decision: str
    reason: str
    tool_name: str
    input_args: dict[str, Any]


class SafeJiraProxy:
    def __init__(self, upstream: UpstreamConnector, policy: JiraPolicy):
        self.upstream = upstream
        self.policy = policy

    async def list_tools(self) -> list[dict[str, Any]]:
        tools = await self.upstream.list_tools()
        return [tool for tool in tools if self.policy.can_expose(tool["name"])]

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        decision, updated, reason = self.policy.decide(tool_name, arguments or {})
        self._log(Decision(decision, reason, tool_name, updated))

        if decision == "DENY":
            return {
                "error": "POLICY_DENY",
                "tool": tool_name,
                "reason": reason,
            }

        if decision == "SIMULATE":
            return {
                "simulated": True,
                "tool": tool_name,
                "message": "Simulated response by proxy policy",
                "arguments": updated,
            }

        return await self.upstream.call_tool(tool_name, updated)

    @staticmethod
    def _log(entry: Decision) -> None:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool_name": entry.tool_name,
            "input": entry.input_args,
            "decision": entry.decision,
            "reason": entry.reason,
        }
        print(json.dumps(payload), flush=True)
