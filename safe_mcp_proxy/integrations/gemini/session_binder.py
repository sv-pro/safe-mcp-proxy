from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple

from safe_mcp_proxy.executor import Executor
from safe_mcp_proxy.integrations.gemini.adapter import ToolCall
from safe_mcp_proxy.integrations.gemini.proxy import GeminiProxy
from safe_mcp_proxy.integrations.gemini.trace import GeminiTraceLogger
from safe_mcp_proxy.main import build_executor

_REPO_ROOT = Path(__file__).resolve().parents[3]

# The fallback world used when no explicit mapping is found.
# Must be restrictive — a missing mapping must never grant more capability.
_DEFAULT_RESTRICTIVE_WORLD = "read_only"


class SessionManifestBinder:
    """Maps Gemini agent_id / session_id to a deterministic World Manifest.

    Each agent identity resolves to exactly one world_id.  The resolved world
    governs the tool surface and policy rules for that agent's execution.

    Default: if no explicit mapping is found for an agent_id (or none is
    provided), the fallback world is the restrictive read_only world.  A
    missing mapping never grants more capability than an explicit one.

    Executors are cached per world_id — the heavy manifest-parse and registry-
    build happens once per world, not per request.

    Usage::

        binder = SessionManifestBinder(
            base_dir=Path("/repo"),
            agent_manifest_map={"agent-prod": "gemini_demo", "agent-ro": "read_only"},
            default_world_id="read_only",
        )
        proxy, world_id = binder.bind(tool_call)
        result = proxy.execute(request)
    """

    def __init__(
        self,
        base_dir: Path = _REPO_ROOT,
        agent_manifest_map: Optional[Dict[str, str]] = None,
        default_world_id: str = _DEFAULT_RESTRICTIVE_WORLD,
    ) -> None:
        self._base_dir = base_dir
        self._agent_map: Dict[str, str] = dict(agent_manifest_map or {})
        self._default_world_id = default_world_id
        self._executor_cache: Dict[str, Executor] = {}

    def resolve_world_id(
        self,
        agent_id: Optional[str],
        session_id: Optional[str] = None,  # noqa: ARG002 — reserved for future use
    ) -> str:
        """Return the world_id for the given agent / session context.

        Lookup order:
          1. agent_id exact match in mapping
          2. default_world_id (restrictive fallback)
        """
        if agent_id and agent_id in self._agent_map:
            return self._agent_map[agent_id]
        return self._default_world_id

    def get_executor(self, world_id: str) -> Executor:
        """Return a cached Executor for the given world_id.

        Manifests are parsed and registries built once per world_id.
        """
        if world_id not in self._executor_cache:
            self._executor_cache[world_id] = build_executor(
                self._base_dir, world_id=world_id
            )
        return self._executor_cache[world_id]

    def bind(
        self,
        tool_call: ToolCall,
        trace_logger: Optional[GeminiTraceLogger] = None,
    ) -> Tuple[GeminiProxy, str]:
        """Resolve the correct GeminiProxy for this tool call's agent context.

        Returns (proxy, world_id) — the world_id is surfaced so callers can
        include it in their own logs without inspecting the executor.
        """
        world_id = self.resolve_world_id(tool_call.agent_id, tool_call.session_id)
        executor = self.get_executor(world_id)
        proxy = GeminiProxy(executor, trace_logger=trace_logger)
        return proxy, world_id
