"""Thread-safe mutable pointer to the currently active world.

WorldController is a singleton owned by build_executor() / the API layer.
All reads and writes go through an RLock so a world switch is atomic
relative to in-flight tool calls that read .world.
"""

import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from safe_mcp_proxy.compiler import compile_world_manifest, resolve_manifest_path


class WorldNotFoundError(FileNotFoundError):
    """Raised when a requested world_id has no matching manifest file."""


class WorldController:
    def __init__(self, initial_world_id: str, base_dir: Path):
        self._base_dir = base_dir
        self._lock = threading.RLock()
        self._history: List[str] = []
        self._world_id = initial_world_id
        self._world = self._compile(initial_world_id)
        self._history.append(initial_world_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compile(self, world_id: str) -> Dict[str, Any]:
        try:
            path = resolve_manifest_path(self._base_dir, world_id or None)
            return compile_world_manifest(str(path))
        except FileNotFoundError as exc:
            raise WorldNotFoundError(str(exc)) from exc

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def world(self) -> Dict[str, Any]:
        """Return the current compiled world config (RLock-protected)."""
        with self._lock:
            return self._world

    def switch(self, world_id: str, reason: str = "") -> Dict[str, Any]:
        """Atomically replace the active world and return a diff dict.

        Keys: from, to, appeared (list), vanished (list), reason.
        Raises WorldNotFoundError if world_id has no manifest.
        """
        new_world = self._compile(world_id)  # compile outside lock (I/O can be slow)
        with self._lock:
            old_id = self._world_id
            old_allowlist = set(self._world.get("allowlist", []))
            new_allowlist = set(new_world.get("allowlist", []))
            self._world = new_world
            self._world_id = world_id
            self._history.append(world_id)

        appeared = sorted(new_allowlist - old_allowlist)
        vanished = sorted(old_allowlist - new_allowlist)
        return {
            "from": old_id,
            "to": world_id,
            "appeared": appeared,
            "vanished": vanished,
            "reason": reason,
        }

    def current_id(self) -> str:
        with self._lock:
            return self._world_id

    @property
    def history(self) -> List[str]:
        with self._lock:
            return list(self._history)

    def list_tools(self) -> List[Dict[str, Any]]:
        """Return exposed tools for the current world as plain dicts."""
        from safe_mcp_proxy.registry import ToolRegistry  # lazy to avoid import cycle

        world = self.world
        registry = ToolRegistry.with_mock_tools(
            allowlist=world.get("allowlist", []),
            capability_defs=world.get("capability_definitions"),
        )
        return [
            {
                "name": t.name,
                "capability": t.capability,
                "side_effect_type": t.side_effect_type,
            }
            for t in registry.list_exposed()
        ]
