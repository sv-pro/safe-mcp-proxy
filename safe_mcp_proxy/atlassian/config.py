from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Set

from .filter import CapabilityFilter


def _parse_tool_set(raw: str) -> Set[str]:
    """Parse a comma-separated tool list from an env var value."""
    return {t.strip() for t in raw.split(",") if t.strip()}


@dataclass
class AtlassianProxyConfig:
    """Runtime config for the Atlassian MCP passthrough.

    mode="proxy"  — requests are forwarded through safe-mcp-proxy (default)
    mode="direct" — clients connect to Atlassian MCP directly; proxy is bypassed

    allowed_tools: empty set → passthrough (all tools visible); non-empty → strict allowlist
    denied_tools:  always hidden regardless of allowlist (composite / unsafe tools)
    """

    upstream_url: str = ""
    mode: str = "proxy"
    timeout: int = 30
    allowed_tools: Set[str] = field(default_factory=set)
    denied_tools: Set[str] = field(default_factory=set)

    @classmethod
    def from_env(cls) -> "AtlassianProxyConfig":
        return cls(
            upstream_url=os.environ.get("ATLASSIAN_MCP_URL", ""),
            mode=os.environ.get("ATLASSIAN_PROXY_MODE", "proxy"),
            timeout=int(os.environ.get("ATLASSIAN_MCP_TIMEOUT", "30")),
            allowed_tools=_parse_tool_set(os.environ.get("ATLASSIAN_ALLOWED_TOOLS", "")),
            denied_tools=_parse_tool_set(os.environ.get("ATLASSIAN_DENIED_TOOLS", "")),
        )

    @property
    def is_proxy_mode(self) -> bool:
        return self.mode == "proxy"

    def capability_filter(self) -> CapabilityFilter:
        return CapabilityFilter(self.allowed_tools, self.denied_tools)
