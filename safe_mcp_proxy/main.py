import argparse
import json
from pathlib import Path
from typing import Optional

import yaml

from safe_mcp_proxy.compiler import compile_world_manifest
from safe_mcp_proxy.executor import Executor
from safe_mcp_proxy.policy_engine import PolicyEngine
from safe_mcp_proxy.provenance import Provenance
from safe_mcp_proxy.registry import ToolRegistry


def _load_simulation_flag(policy_path: Path) -> bool:
    with policy_path.open("r", encoding="utf-8") as handle:
        cfg = yaml.safe_load(handle) or {}
    return bool(cfg.get("simulation", {}).get("external_side_effects", False))


def build_executor(base_dir: Path, world_id: Optional[str] = None) -> Executor:
    if world_id is None:
        manifest_path = base_dir / "world_manifest.yaml"
    else:
        manifest_path = base_dir / "worlds" / f"{world_id}.yaml"
        if not manifest_path.exists():
            raise FileNotFoundError(f"World manifest not found: {manifest_path}")
    manifest_tables = compile_world_manifest(str(manifest_path))
    registry = ToolRegistry.with_mock_tools(allowlist=manifest_tables["allowlist"])
    policy_engine = PolicyEngine(
        allowlist=manifest_tables["allowlist"],
        capability_map=manifest_tables["capability_map"],
    )
    simulate_external = _load_simulation_flag(base_dir / "safe_mcp_proxy" / "config" / "policy.yaml")
    return Executor(
        registry=registry,
        policy_engine=policy_engine,
        audit_log_path=str(base_dir / "safe_mcp_proxy" / "logs" / "audit.jsonl"),
        simulate_external=simulate_external,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Minimal Safe MCP Proxy prototype")
    parser.add_argument("--tool", required=True)
    parser.add_argument("--source", default="cli", choices=["cli", "email", "web", "tool_output"])
    parser.add_argument("--payload", default="{}", help="JSON payload")
    parser.add_argument("--world", default=None, help="World ID (loads worlds/<world_id>.yaml)")
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parents[1]
    executor = build_executor(base_dir, world_id=args.world)
    provenance = Provenance.from_source(args.source)
    payload = json.loads(args.payload)
    result = executor.execute(args.tool, payload, provenance)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
