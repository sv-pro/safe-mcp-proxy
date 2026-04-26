from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .adapters import apply_safe_abstraction, ATLASSIAN_TOOLS
from .config import AtlassianProxyConfig
from .flow import FlowContext
from .policy import ManifestPolicyEngine, PolicyDecision
from safe_mcp_proxy.provenance import TAINTED_CHANNELS


class MCPPassthrough:
    """MCP passthrough with policy enforcement and provenance-lite flow tracking.

    Pipeline for tools/call:
      1. Policy gate  — ABSENT / DENY / ALLOW
      2. Forward      — to upstream or stub
      3. Safe abstraction — truncate raw confluence content
      4. Tag output   — update FlowContext with data label
      5. Debug info   — optionally attach flow state to response
    """

    def __init__(
        self,
        config: AtlassianProxyConfig,
        log_path: Optional[Path] = None,
        policy: Optional[ManifestPolicyEngine] = None,
        flow_context: Optional[FlowContext] = None,
    ) -> None:
        self._config = config
        self._log_path = log_path
        self._policy = policy
        self._flow = flow_context

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def forward(self, request: Dict[str, Any]) -> Dict[str, Any]:
        method = request.get("method", "")
        self._log({"direction": "request", "payload": request})

        # ---- Policy gate (tools/call only) ----------------------------
        if method == "tools/call" and self._policy is not None:
            params = request.get("params") or {}
            tool_name = params.get("name", "")
            arguments = params.get("arguments") or {}
            tainted = self._config.source_channel in TAINTED_CHANNELS
            decision = self._policy.evaluate(
                tool_name, arguments, tainted, flow_context=self._flow
            )
            self._log_decision(request, decision)
            if decision.decision != "ALLOW":
                response = _blocked_response(request.get("id"), decision)
                self._log({"direction": "response", "payload": response})
                return response

        # ---- Forward --------------------------------------------------
        if not self._config.upstream_url or not self._config.is_proxy_mode:
            response = self._stub_response(request)
        else:
            try:
                response = self._http_forward(request)
            except (urllib.error.URLError, OSError) as exc:
                response = _error_response(request.get("id"), -32603, str(exc))

        # ---- Post-processing for tools/call ---------------------------
        if method == "tools/call" and "result" in response:
            params = request.get("params") or {}
            tool_name = params.get("name", "")

            # Safe abstraction (M4): truncate raw content
            was_abstracted = ATLASSIAN_TOOLS.get(tool_name) is not None and \
                ATLASSIAN_TOOLS[tool_name].safe_alias is not None
            response = apply_safe_abstraction(tool_name, response)

            # Tag output (M5): update flow context
            if self._flow is not None:
                self._flow.tag_output(tool_name, was_abstracted=was_abstracted)

        # ---- Capability filtering for tools/list ----------------------
        if method == "tools/list" and "result" in response:
            response = self._config.capability_filter().apply_to_list_response(response)

        # ---- Debug mode -----------------------------------------------
        if self._config.debug and self._flow is not None and "result" in response:
            result = dict(response["result"])
            result["_debug"] = {"flow_context": self._flow.as_dict()}
            response = {**response, "result": result}

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

    def _log_decision(self, request: Dict[str, Any], decision: PolicyDecision) -> None:
        self._log({
            "direction": "decision",
            "tool": decision.tool,
            "decision": decision.decision,
            "rule": decision.rule,
            "tainted": decision.tainted,
            "request_id": request.get("id"),
            "flow_labels": sorted(self._flow.active_labels()) if self._flow else [],
        })


def _error_response(req_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def _blocked_response(req_id: Any, decision: PolicyDecision) -> Dict[str, Any]:
    if decision.decision == "ABSENT":
        message = f"Action does not exist in this world: {decision.tool!r}"
    else:
        message = f"Action blocked by policy ({decision.rule}): {decision.tool!r}"
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {
            "code": -32601,
            "message": message,
            "data": {"decision": decision.decision, "rule": decision.rule},
        },
    }
