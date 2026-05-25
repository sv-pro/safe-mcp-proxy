"""OPA-backed policy engine — subprocess and REST evaluation strategies."""

from __future__ import annotations

import json
import shutil
import subprocess
import urllib.error
import urllib.request
from typing import Dict, Iterable

from safe_mcp_proxy.compiler import build_opa_input
from safe_mcp_proxy.decision import Decision
from safe_mcp_proxy.policy_engine import PolicyResult

_OPA_PACKAGE = "data.safe_mcp_proxy.decision"
_DEFAULT_REST_URL = "http://localhost:8181/v1/data/safe_mcp_proxy/decision"


class OPAPolicyEngine:
    """Evaluates decisions via OPA/Rego; drop-in replacement for PolicyEngine."""

    def __init__(
        self,
        policy_path: str,
        allowlist: Iterable[str],
        capability_map: Dict[str, bool],
        evaluator: str = "subprocess",
        opa_url: str = _DEFAULT_REST_URL,
        approval_required: Iterable[str] = (),
    ) -> None:
        self._policy_path = policy_path
        self._allowlist = list(allowlist)
        self._capability_map = dict(capability_map)
        self._evaluator = evaluator
        self._opa_url = opa_url
        self._approval_required = list(approval_required)

        if evaluator == "subprocess" and shutil.which("opa") is None:
            raise RuntimeError(
                "OPA binary not found on PATH. "
                "Install it from https://www.openpolicyagent.org/docs/latest/#running-opa "
                "or switch to evaluator='rest' and run `opa run --server`."
            )

    def decide(
        self,
        tool_name: str,
        capability: str,
        taint: bool,
        side_effect_type: str,
        descriptor_hash_valid: bool,
    ) -> PolicyResult:
        opa_input = build_opa_input(
            tool_name=tool_name,
            capability=capability,
            taint=taint,
            side_effect_type=side_effect_type,
            descriptor_hash_valid=descriptor_hash_valid,
            allowlist=self._allowlist,
            capability_map=self._capability_map,
            approval_required=self._approval_required,
        )

        if self._evaluator == "rest":
            raw = self._eval_rest(opa_input)
        else:
            raw = self._eval_subprocess(opa_input)

        return PolicyResult(
            decision=Decision(raw["decision"]),
            rule_hit=raw["rule"],
        )

    def _eval_subprocess(self, opa_input: dict) -> dict:
        input_json = json.dumps(opa_input)
        cmd = [
            "opa",
            "eval",
            "--data", self._policy_path,
            "--input", "/dev/stdin",
            "--format", "raw",
            _OPA_PACKAGE,
        ]
        try:
            proc = subprocess.run(
                cmd,
                input=input_json,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("OPA binary not found — install OPA or use evaluator='rest'.") from exc

        if proc.returncode != 0:
            raise RuntimeError(
                f"OPA subprocess exited with code {proc.returncode}.\n"
                f"stderr: {proc.stderr.strip()}"
            )

        try:
            return json.loads(proc.stdout.strip())
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"OPA returned non-JSON output: {proc.stdout!r}"
            ) from exc

    def _eval_rest(self, opa_input: dict) -> dict:
        body = json.dumps({"input": opa_input}).encode("utf-8")
        req = urllib.request.Request(
            self._opa_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"OPA REST call failed ({self._opa_url}): {exc}"
            ) from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError("OPA REST response was not valid JSON.") from exc

        # OPA REST API wraps the result in {"result": ...}
        result = payload.get("result")
        if result is None:
            raise RuntimeError(
                f"OPA REST response missing 'result' key. Full response: {payload}"
            )
        return result
