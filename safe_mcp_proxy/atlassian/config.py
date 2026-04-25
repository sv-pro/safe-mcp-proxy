from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Set

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

    manifest_path: path to a world manifest YAML with policy rules; None → no enforcement
    source_channel: provenance channel for incoming requests ("cli", "web", etc.)
    """

    upstream_url: str = ""
    mode: str = "proxy"
    timeout: int = 30
    allowed_tools: Set[str] = field(default_factory=set)
    denied_tools: Set[str] = field(default_factory=set)
    manifest_path: Optional[Path] = None
    source_channel: str = "cli"

    @classmethod
    def from_env(cls) -> "AtlassianProxyConfig":
        raw_manifest = os.environ.get("ATLASSIAN_MANIFEST_PATH", "")
        return cls(
            upstream_url=os.environ.get("ATLASSIAN_MCP_URL", ""),
            mode=os.environ.get("ATLASSIAN_PROXY_MODE", "proxy"),
            timeout=int(os.environ.get("ATLASSIAN_MCP_TIMEOUT", "30")),
            allowed_tools=_parse_tool_set(os.environ.get("ATLASSIAN_ALLOWED_TOOLS", "")),
            denied_tools=_parse_tool_set(os.environ.get("ATLASSIAN_DENIED_TOOLS", "")),
            manifest_path=Path(raw_manifest) if raw_manifest else None,
            source_channel=os.environ.get("ATLASSIAN_SOURCE_CHANNEL", "cli"),
        )

    @property
    def is_proxy_mode(self) -> bool:
        return self.mode == "proxy"

    def capability_filter(self) -> CapabilityFilter:
        return CapabilityFilter(self.allowed_tools, self.denied_tools)
