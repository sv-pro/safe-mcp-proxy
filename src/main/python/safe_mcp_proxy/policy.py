from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class JiraPolicy:
    mode: str
    allowed_jql: str
    allowed_actions: set[str]
    denied_actions: set[str]
    simulate: bool = False

    @classmethod
    def load(cls, path: str | Path) -> "JiraPolicy":
        data = yaml.safe_load(Path(path).read_text())
        jira = data.get("jira", {})
        return cls(
            mode=data.get("mode", "default"),
            allowed_jql=jira.get("allowed_jql", ""),
            allowed_actions=set(jira.get("allowed_actions", [])),
            denied_actions=set(jira.get("denied_actions", [])),
            simulate=bool(data.get("simulate", False)),
        )

    def can_expose(self, tool_name: str) -> bool:
        if tool_name in self.denied_actions:
            return False
        if self.allowed_actions and tool_name not in self.allowed_actions:
            return False
        return True

    def decide(self, tool_name: str, arguments: dict[str, Any]) -> tuple[str, dict[str, Any], str]:
        if tool_name in self.denied_actions:
            if self.simulate:
                return "SIMULATE", arguments, "tool is explicitly denied"
            return "DENY", arguments, "tool is explicitly denied"

        if self.allowed_actions and tool_name not in self.allowed_actions:
            return "DENY", arguments, "tool is not in allowed_actions"

        updated = dict(arguments or {})
        # Jira read style tools often accept 'jql' or 'query'. Constrain both deterministically.
        if "jql" in updated or tool_name == "read_issue":
            incoming = updated.get("jql", "").strip()
            if incoming:
                updated["jql"] = f"({incoming}) AND ({self.allowed_jql})"
            else:
                updated["jql"] = self.allowed_jql
            return "MODIFY", updated, "jql constrained by policy"

        if "query" in updated:
            incoming = updated.get("query", "").strip()
            if incoming:
                updated["query"] = f"({incoming}) AND ({self.allowed_jql})"
            else:
                updated["query"] = self.allowed_jql
            return "MODIFY", updated, "query constrained by policy"

        return "ALLOW", updated, "allowed by policy"
