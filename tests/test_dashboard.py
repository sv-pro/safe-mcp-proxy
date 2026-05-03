"""
Integration tests for the audit dashboard (EPIC 14).

Unit tests for individual dashboard endpoints live in TestDashboard inside
tests/test_api.py. This file covers end-to-end scenarios:
  - /stats reflects decisions generated through the executor
  - /worlds/current matches the active world manifest
  - /dashboard returns a complete, valid HTML page
  - dashboard_demo.py exits 0
"""
import asyncio
import json
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

import httpx

BASE_DIR = Path(__file__).resolve().parents[1]


def _build_test_app(world_yaml: str | None = None):
    """Create a fully wired FastAPI app with a fresh temp audit log."""
    import hashlib
    from safe_mcp_proxy.approval_store import ApprovalStore
    from safe_mcp_proxy.compiler import compile_world_manifest
    from safe_mcp_proxy.executor import Executor
    from safe_mcp_proxy.main import _build_policy_engine
    from safe_mcp_proxy.registry import ToolRegistry
    from api.main import create_app

    tmp = Path(tempfile.mkdtemp())
    manifest_yaml = world_yaml or textwrap.dedent("""\
        world_id: test
        allowed_tools: [read_file, list_repo, send_email]
        capabilities:
          read_file:  {allowed: true}
          list_repo:  {allowed: true}
          send_email: {allowed: true}
          dangerous_exec: {allowed: false}
        taint_rules:
          - tainted_external: deny
        side_effects: {external: restricted}
    """)
    (tmp / "world_manifest.yaml").write_text(manifest_yaml, encoding="utf-8")
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
        world_id=tables.get("world_id", ""),
        policy_version=pv,
    )
    app = create_app(tmp, executor=executor)
    return app, executor, tmp


class TestDashboardIntegration(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.app, self.executor, self.tmp = _build_test_app()

    async def asyncTearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    async def _get(self, path: str):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(path)

    async def _seed(self, n_allow=3, n_deny=2, n_absent=1):
        from safe_mcp_proxy.provenance import Provenance
        for _ in range(n_allow):
            self.executor.execute("read_file", {"path": "x"}, Provenance.from_source("cli"))
        for _ in range(n_deny):
            self.executor.execute("send_email", {"to": "a@b.c", "body": ""}, Provenance.from_source("web"))
        for _ in range(n_absent):
            self.executor.execute("no_such_tool", {}, Provenance.from_source("cli"))

    # ── /stats ───────────────────────────────────────────────────────────

    async def test_stats_counts_match_generated_decisions(self):
        await self._seed(n_allow=3, n_deny=2, n_absent=1)
        resp = await self._get("/stats")
        self.assertEqual(resp.status_code, 200)
        counts = resp.json()["counts"]
        self.assertEqual(counts["ALLOW"],  3)
        self.assertEqual(counts["DENY"],   2)
        self.assertEqual(counts["ABSENT"], 1)
        self.assertEqual(resp.json()["total"], 6)

    async def test_stats_empty_log_returns_zeros(self):
        resp = await self._get("/stats")
        self.assertEqual(resp.json()["total"], 0)
        self.assertEqual(resp.json()["counts"]["DENY"], 0)

    # ── /worlds/current ──────────────────────────────────────────────────

    async def test_worlds_current_world_id_matches_manifest(self):
        resp = await self._get("/worlds/current")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["world_id"], "test")

    async def test_worlds_current_only_shows_allowed_tools(self):
        resp = await self._get("/worlds/current")
        names = {t["name"] for t in resp.json()["tools"]}
        self.assertIn("read_file", names)
        self.assertNotIn("dangerous_exec", names)

    async def test_worlds_current_side_effect_types_are_valid(self):
        resp = await self._get("/worlds/current")
        for tool in resp.json()["tools"]:
            self.assertIn(tool["side_effect_type"], ("read", "internal", "external"))

    # ── /dashboard ────────────────────────────────────────────────────────

    async def test_dashboard_contains_all_required_elements(self):
        resp = await self._get("/dashboard")
        self.assertEqual(resp.status_code, 200)
        body = resp.text
        for element in ('id="feed"', 'id="stats-bar"', 'id="surface"',
                         "PALETTES", "EventSource", "localStorage"):
            self.assertIn(element, body, f"Missing: {element}")

    async def test_dashboard_accessible_palette_no_red_green_for_allow_deny(self):
        body = (await self._get("/dashboard")).text
        # accessible block uses blue for ALLOW and orange for DENY
        self.assertIn("0077bb", body)   # ALLOW blue
        self.assertIn("ee7733", body)   # DENY orange
        # neither pure green nor pure red appears as ALLOW/DENY in accessible
        accessible_block_start = body.index("accessible")
        accessible_snippet = body[accessible_block_start: accessible_block_start + 300]
        self.assertNotIn("388e3c", accessible_snippet)  # traffic green
        self.assertNotIn("c62828", accessible_snippet)  # traffic red


class TestDashboardDemo(unittest.TestCase):
    def test_dashboard_demo_exits_zero(self):
        result = subprocess.run(
            [sys.executable, "-m", "safe_mcp_proxy.examples.dashboard_demo"],
            capture_output=True,
            text=True,
            cwd=str(BASE_DIR),
            timeout=30,
        )
        self.assertEqual(
            result.returncode, 0,
            msg=f"demo failed:\nstdout: {result.stdout}\nstderr: {result.stderr}",
        )
        self.assertIn("DEMO PASS", result.stdout)

    def test_dashboard_demo_outputs_all_sections(self):
        result = subprocess.run(
            [sys.executable, "-m", "safe_mcp_proxy.examples.dashboard_demo"],
            capture_output=True, text=True,
            cwd=str(BASE_DIR), timeout=30,
        )
        for section in ("GENERATING 10 DECISIONS", "STATS BAR", "TOOL SURFACE", "DASHBOARD"):
            self.assertIn(section, result.stdout)


if __name__ == "__main__":
    unittest.main()
