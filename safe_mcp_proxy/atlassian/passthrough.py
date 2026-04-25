from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .config import AtlassianProxyConfig


class MCPPassthrough:
    """Stateless MCP passthrough: forward JSON-RPC requests to an upstream
    Atlassian MCP server and log every request/response pair."""

    def __init__(
        self,
        config: AtlassianProxyConfig,
        log_path: Optional[Path] = None,
    ) -> None:
        self._config = config
        self._log_path = log_path

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def forward(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Forward one MCP JSON-RPC request; return the response dict."""
        self._log({"direction": "request", "payload": request})

        if not self._config.upstream_url or not self._config.is_proxy_mode:
            response = self._stub_response(request)
        else:
            try:
                response = self._http_forward(request)
            except (urllib.error.URLError, OSError) as exc:
                response = _error_response(request.get("id"), -32603, str(exc))

        if request.get("method") == "tools/list" and "result" in response:
            response = self._config.capability_filter().apply_to_list_response(response)

        self._log({"direction": "response", "payload": response})
        return response

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _http_forward(self, request: Dict[str, Any]) -> Dict[str, Any]:
        body = json.dumps(request).encode()
        req = urllib.request.Request(
            self._config.upstream_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self._config.timeout) as resp:
            return json.loads(resp.read())

    def _stub_response(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Return a minimal valid response when upstream is not configured."""
        method = request.get("method", "")
        req_id = request.get("id")

        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": []}}

        if method == "tools/call":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": "Upstream not configured"}],
                    "isError": True,
                },
            }

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "safe-mcp-proxy/atlassian", "version": "0.1.0"},
                },
            }

        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    def _log(self, entry: Dict[str, Any]) -> None:
        if self._log_path is None:
            return
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        entry["timestamp"] = datetime.now(timezone.utc).isoformat()
        with self._log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")


def _error_response(req_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}
