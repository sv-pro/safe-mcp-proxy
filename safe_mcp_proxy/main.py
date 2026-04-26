import argparse
import hashlib
import json
from pathlib import Path
from typing import Optional, Union

import yaml

from safe_mcp_proxy.approval_store import ApprovalStore
from safe_mcp_proxy.compiler import compile_world_manifest
from safe_mcp_proxy.execution_mode import ExecutionMode
from safe_mcp_proxy.executor import Executor
from safe_mcp_proxy.opa_engine import OPAPolicyEngine
from safe_mcp_proxy.policy_engine import PolicyEngine
from safe_mcp_proxy.provenance import Provenance
from safe_mcp_proxy.registry import ToolRegistry


def _load_simulation_flag(policy_path: Path) -> bool:
    with policy_path.open("r", encoding="utf-8") as handle:
        cfg = yaml.safe_load(handle) or {}
    return bool(cfg.get("simulation", {}).get("external_side_effects", False))


def _resolve_manifest_path(base_dir: Path, world_id: Optional[str]) -> Path:
    if world_id is None:
        return base_dir / "world_manifest.yaml"

    candidates = [
        base_dir / "safe_mcp_proxy" / "config" / "worlds" / f"{world_id}.yaml",
        base_dir / "worlds" / f"{world_id}.yaml",
    ]
    for manifest_path in candidates:
        if manifest_path.exists():
            return manifest_path

    searched = ", ".join(str(path) for path in candidates)
    raise FileNotFoundError(f"World manifest not found for world_id={world_id!r}. Searched: {searched}")


def _build_policy_engine(
    manifest_tables: dict,
    engine: str,
    base_dir: Path,
) -> Union[PolicyEngine, OPAPolicyEngine]:
    approval_required = manifest_tables.get("approval_required", [])
    if engine == "opa":
        policy_path = str(base_dir / "safe_mcp_proxy" / "policies" / "proxy.rego")
        return OPAPolicyEngine(
            policy_path=policy_path,
            allowlist=manifest_tables["allowlist"],
            capability_map=manifest_tables["capability_map"],
            approval_required=approval_required,
        )
    return PolicyEngine(
        allowlist=manifest_tables["allowlist"],
        capability_map=manifest_tables["capability_map"],
        approval_required=approval_required,
    )


def build_executor(
    base_dir: Path,
    world_id: Optional[str] = None,
    engine: Optional[str] = None,
) -> Executor:
    manifest_path = _resolve_manifest_path(base_dir, world_id)
    manifest_tables = compile_world_manifest(str(manifest_path))
    policy_version = hashlib.sha256(manifest_path.read_bytes()).hexdigest()[:8]
    registry = ToolRegistry.with_mock_tools(
        allowlist=manifest_tables["allowlist"],
        capability_defs=manifest_tables.get("capability_definitions"),
    )
    # CLI --engine flag overrides the manifest's policy_engine key; default is "python"
    resolved_engine = engine if engine is not None else manifest_tables.get("policy_engine", "python")
    policy_engine = _build_policy_engine(manifest_tables, resolved_engine, base_dir)
    simulate_external = _load_simulation_flag(base_dir / "safe_mcp_proxy" / "config" / "policy.yaml")
    return Executor(
        registry=registry,
        policy_engine=policy_engine,
        audit_log_path=str(base_dir / "safe_mcp_proxy" / "logs" / "audit.jsonl"),
        simulate_external=simulate_external,
        approval_store=ApprovalStore(),
        world_id=manifest_tables.get("world_id", ""),
        policy_version=policy_version,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Minimal Safe MCP Proxy prototype")
    parser.add_argument("--tool", required=True)
    parser.add_argument("--source", default="cli", choices=["cli", "email", "web", "tool_output"])
    parser.add_argument("--payload", default="{}", help="JSON payload")
    parser.add_argument("--world", default=None, help="World ID (loads safe_mcp_proxy/config/worlds/<world_id>.yaml, falls back to worlds/<world_id>.yaml)")
    parser.add_argument("--engine", default=None, choices=["python", "opa"], help="Policy engine to use: 'python' (default) or 'opa'. Overrides the manifest's policy_engine key.")
    parser.add_argument("--mode", default="interactive", choices=["interactive", "background"], help="Execution mode: 'interactive' (default) allows ASK; 'background' converts ASK to DENY.")
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parents[1]
    executor = build_executor(base_dir, world_id=args.world, engine=args.engine)
    mode = ExecutionMode(args.mode.upper())
    provenance = Provenance.from_source(args.source, execution_mode=mode)
    payload = json.loads(args.payload)
    result = executor.execute(args.tool, payload, provenance)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
