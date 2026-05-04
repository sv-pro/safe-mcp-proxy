"""
Dashboard demo — generates 10 diverse audit decisions and verifies the three
dashboard API endpoints respond correctly.

Run:
    python -m demos.product.dashboard.demo
"""
import asyncio
import hashlib
import shutil
import sys
import tempfile
import textwrap
from pathlib import Path

import httpx

BASE_DIR = Path(__file__).resolve().parents[3]

_SCENARIOS = [
    ("read_file",     {"path": "README.md"},           "cli"),    # ALLOW
    ("list_repo",     {},                              "cli"),    # ALLOW
    ("read_file",     {"path": "safe_mcp_proxy/"},     "cli"),    # ALLOW
    ("send_email",    {"to": "x@y.z", "body": "leak"}, "web"),   # DENY taint
    ("send_email",    {"to": "x@y.z", "body": "leak"}, "email"), # DENY taint
    ("read_file",     {"path": "tests/"},              "cli"),    # ALLOW
    ("dangerous_exec",{"command": "ls"},               "cli"),    # ABSENT
    ("read_file",     {"path": "api/"},                "cli"),    # ALLOW
    ("list_repo",     {},                              "cli"),    # ALLOW
    ("no_such_tool",  {},                              "cli"),    # ABSENT
]


def _section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print("=" * 60)


def _row(label: str, value) -> None:
    print(f"  {label:<30} {value}")


def _make_app():
    from safe_mcp_proxy.approval_store import ApprovalStore
    from safe_mcp_proxy.compiler import compile_world_manifest
    from safe_mcp_proxy.executor import Executor
    from safe_mcp_proxy.main import _build_policy_engine
    from safe_mcp_proxy.registry import ToolRegistry
    from api.main import create_app

    tmp = Path(tempfile.mkdtemp())
    (tmp / "world_manifest.yaml").write_text(textwrap.dedent("""\
        world_id: demo
        allowed_tools: [read_file, list_repo, send_email]
        capabilities:
          read_file:     {allowed: true,  side_effect_type: read}
          list_repo:     {allowed: true,  side_effect_type: internal}
          send_email:    {allowed: true,  side_effect_type: external}
          dangerous_exec:{allowed: false}
        taint_rules:
          - tainted_external: deny
        side_effects: {external: restricted}
    """), encoding="utf-8")
    cfg = tmp / "safe_mcp_proxy" / "config"
    cfg.mkdir(parents=True)
    (cfg / "policy.yaml").write_text(
        "simulation:\n  external_side_effects: true\n", encoding="utf-8"
    )
    logs = tmp / "safe_mcp_proxy" / "logs"
    logs.mkdir(parents=True)
    audit = logs / "audit.jsonl"
    audit.write_text("", encoding="utf-8")

    manifest_path = tmp / "world_manifest.yaml"
    tables = compile_world_manifest(str(manifest_path))
    pv = hashlib.sha256(manifest_path.read_bytes()).hexdigest()[:8]
    registry = ToolRegistry.with_mock_tools(tables["allowlist"])
    engine = _build_policy_engine(tables, "python", tmp)
    executor = Executor(
        registry=registry,
        policy_engine=engine,
        audit_log_path=audit,
        simulate_external=True,
        approval_store=ApprovalStore(),
        world_id="demo",
        policy_version=pv,
    )
    app = create_app(tmp, executor=executor)
    return app, executor, tmp


async def main() -> None:
    from safe_mcp_proxy.provenance import Provenance

    app, executor, tmp = _make_app()
    try:
        _section("1. GENERATING 10 DECISIONS")
        for tool, payload, source in _SCENARIOS:
            prov = Provenance.from_source(source)
            result = executor.execute(tool, payload, prov)
            _row(f"{tool} ({source})", f"{result['decision']} — {result['rule']}")

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            stats  = (await client.get("/stats")).json()
            worlds = (await client.get("/worlds/current")).json()
            dash   = await client.get("/dashboard")

        _section("2. STATS BAR — GET /stats")
        for d, cnt in stats["counts"].items():
            _row(d, cnt)
        _row("total", stats["total"])

        _section("3. TOOL SURFACE — GET /worlds/current")
        _row("world_id", worlds["world_id"])
        for t in worlds["tools"]:
            _row(t["name"], t["side_effect_type"])

        _section("4. DASHBOARD — GET /dashboard")
        _row("status", dash.status_code)
        _row('id="feed" present', 'id="feed"' in dash.text)
        _row('id="stats-bar" present', 'id="stats-bar"' in dash.text)
        _row('id="surface" present', 'id="surface"' in dash.text)
        _row("PALETTES defined", "PALETTES" in dash.text)
        _row("accessible palette present", "accessible" in dash.text)

        assert stats["total"] == 10,         f"Expected 10 total, got {stats['total']}"
        assert stats["counts"]["ALLOW"]  > 0, "Expected ALLOW decisions"
        assert stats["counts"]["DENY"]   > 0, "Expected DENY decisions"
        assert stats["counts"]["ABSENT"] > 0, "Expected ABSENT decisions"
        assert len(worlds["tools"])      > 0, "Expected non-empty tool surface"
        assert dash.status_code == 200,       "Dashboard must return 200"
        assert 'id="feed"'      in dash.text, "Dashboard must contain #feed"
        assert 'id="stats-bar"' in dash.text, "Dashboard must contain #stats-bar"
        assert 'id="surface"'   in dash.text, "Dashboard must contain #surface"

        print("\n" + "=" * 60)
        print("  Dashboard demo — DEMO PASS")
        print()
        print("  To see the live dashboard:")
        print("    uvicorn api.main:app --reload")
        print("    open http://localhost:8000/dashboard")
        print("=" * 60 + "\n")

    except AssertionError as exc:
        print(f"\n  DEMO FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(main())
