from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class AtlassianProxyConfig:
    """Runtime config for the Atlassian MCP passthrough.

    mode="proxy"  — requests are forwarded through safe-mcp-proxy (default)
    mode="direct" — clients connect to Atlassian MCP directly; proxy is bypassed
    """

    upstream_url: str = ""
    mode: str = "proxy"
    timeout: int = 30

    @classmethod
    def from_env(cls) -> "AtlassianProxyConfig":
        return cls(
            upstream_url=os.environ.get("ATLASSIAN_MCP_URL", ""),
            mode=os.environ.get("ATLASSIAN_PROXY_MODE", "proxy"),
            timeout=int(os.environ.get("ATLASSIAN_MCP_TIMEOUT", "30")),
        )

    @property
    def is_proxy_mode(self) -> bool:
        return self.mode == "proxy"
