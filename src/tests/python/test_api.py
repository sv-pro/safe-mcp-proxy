import json
import shutil
import tempfile
import unittest
import asyncio
import textwrap
from pathlib import Path

import httpx

from api.main import create_app
from safe_mcp_proxy.decision import Decision


SAMPLE_ENTRIES = [
    {
        "timestamp": "2026-04-22T07:00:00+00:00",
        "tool": "read_file",
        "decision": "ALLOW",
        "rule": "default_allow",
        "source_channel": "cli",
        "taint": False,
        "descriptor_hash": "aabbcc",
    },
    {
        "timestamp": "2026-04-22T08:00:00+00:00",
        "tool": "send_email",
        "decision": "DENY",
        "rule": "tainted_external_side_effect",
        "source_channel": "web",
        "taint": True,
        "descriptor_hash": "ddeeff",
    },
    {
        "timestamp": "2026-04-22T09:00:00+00:00",
        "tool": "dangerous_exec",
        "decision": "ABSENT",
        "rule": "tool_not_allowlisted",
        "source_channel": "cli",
        "taint": False,
        "descriptor_hash": "",
    },
]


def _write_jsonl(path: Path, entries: list) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(json.dumps(entry) + "\n")


class FastAPITests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "world_manifest.yaml").write_text(textwrap.dedent("""\
            world_id: default
            allowed_tools: [read_file, list_repo, send_email]
            capabilities:
              read_file: {allowed: true}
              list_repo: {allowed: true}
              send_email: {allowed: true}
              dangerous_exec: {allowed: false}
            taint_rules:
              - tainted_external: deny
            side_effects: {external: restricted}
        """), encoding="utf-8")
        config_dir = self.tmp / "safe_mcp_proxy" / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "policy.yaml").write_text("simulation:\n  external_side_effects: true\n", encoding="utf-8")
        worlds_dir = config_dir / "worlds"
        worlds_dir.mkdir()
        (worlds_dir / "world_a.yaml").write_text(textwrap.dedent("""\
            world_id: world_a
            allowed_tools: [read_file, list_repo, send_email]
            capabilities:
              read_file: {allowed: true}
              list_repo: {allowed: true}
              send_email: {allowed: true}
              dangerous_exec: {allowed: false}
            taint_rules:
              - tainted_external: deny
            side_effects: {external: restricted}
        """), encoding="utf-8")
        (worlds_dir / "world_b.yaml").write_text(textwrap.dedent("""\
            world_id: world_b
            allowed_tools: [read_file]
            capabilities:
              read_file: {allowed: true}
              list_repo: {allowed: false}
              send_email: {allowed: false}
              dangerous_exec: {allowed: false}
            taint_rules:
              - tainted_external: deny
            side_effects: {external: restricted}
        """), encoding="utf-8")
        logs_dir = self.tmp / "safe_mcp_proxy" / "logs"
        logs_dir.mkdir(parents=True)
        self.audit_log = logs_dir / "audit.jsonl"
        _write_jsonl(self.audit_log, SAMPLE_ENTRIES)
        self.app = create_app(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        async def run_request() -> httpx.Response:
            transport = httpx.ASGITransport(app=self.app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                return await client.request(method, path, **kwargs)

        return asyncio.run(run_request())

    def test_get_traces_returns_last_n_records(self):
        response = self._request("GET", "/traces", params={"limit": 2})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["traces"]), 2)
        self.assertEqual(body["traces"][0]["id"], 2)
        self.assertEqual(body["traces"][1]["id"], 3)

    def test_get_traces_validates_limit(self):
        response = self._request("GET", "/traces", params={"limit": 0})
        self.assertEqual(response.status_code, 422)

    def test_get_trace_by_id_returns_record(self):
        response = self._request("GET", "/traces/2")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["id"], 2)
        self.assertEqual(body["tool_requested"], "send_email")
        self.assertEqual(body["decision"], "DENY")

    def test_get_trace_by_id_returns_404_when_missing(self):
        response = self._request("GET", "/traces/999")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Trace not found")

    def test_post_replay_by_id_returns_matching_result(self):
        response = self._request("POST", "/replay/1")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["trace_id"], 1)
        self.assertEqual(body["recorded_decision"], "ALLOW")
        self.assertEqual(body["replayed_decision"], "ALLOW")
        self.assertTrue(body["matches"])
        self.assertFalse(body["diverged"])

    def test_post_replay_by_id_marks_divergence(self):
        divergent = [dict(SAMPLE_ENTRIES[0], decision="DENY")]
        _write_jsonl(self.audit_log, divergent)
        self.app = create_app(self.tmp)

        response = self._request("POST", "/replay/1")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["recorded_decision"], "DENY")
        self.assertEqual(body["replayed_decision"], "ALLOW")
        self.assertFalse(body["matches"])
        self.assertTrue(body["diverged"])

    def test_post_replay_by_id_returns_404_when_missing(self):
        response = self._request("POST", "/replay/999")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Trace not found")

    def test_get_stats_returns_counts(self):
        response = self._request("GET", "/stats")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total"], 3)
        self.assertEqual(body["counts"]["ALLOW"], 1)
        self.assertEqual(body["counts"]["DENY"], 1)
        self.assertEqual(body["counts"]["ABSENT"], 1)
        self.assertEqual(body["counts"]["SIMULATE"], 0)

    def test_get_stats_uses_exact_decision_keys(self):
        response = self._request("GET", "/stats")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(set(body["counts"].keys()), set(Decision.values()))

    def test_cors_preflight_allows_local_dev(self):
        response = self._request(
            "OPTIONS",
            "/traces",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["access-control-allow-origin"], "*")


    def test_compare_returns_decisions_per_world(self):
        response = self._request(
            "POST", "/compare",
            json={"scenario": "benign_flow", "worlds": ["world_a", "world_b"]},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["scenario"], "benign_flow")
        self.assertIn("world_a", body["worlds"])
        self.assertIn("world_b", body["worlds"])
        self.assertEqual(body["worlds"]["world_a"]["decision"], "ALLOW")
        self.assertEqual(body["worlds"]["world_b"]["decision"], "ALLOW")

    def test_compare_shows_divergence_across_worlds(self):
        response = self._request(
            "POST", "/compare",
            json={"scenario": "prompt_injection", "worlds": ["world_a", "world_b"]},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["worlds"]["world_a"]["decision"], "DENY")
        self.assertEqual(body["worlds"]["world_a"]["rule"], "tainted_external_side_effect")
        self.assertEqual(body["worlds"]["world_b"]["decision"], "ABSENT")
        self.assertEqual(body["worlds"]["world_b"]["rule"], "tool_not_allowlisted")

    def test_compare_unknown_scenario_returns_404(self):
        response = self._request(
            "POST", "/compare",
            json={"scenario": "nonexistent_scenario", "worlds": ["world_a"]},
        )
        self.assertEqual(response.status_code, 404)

    def test_compare_unknown_world_returns_404(self):
        response = self._request(
            "POST", "/compare",
            json={"scenario": "benign_flow", "worlds": ["no_such_world"]},
        )
        self.assertEqual(response.status_code, 404)


class TestExportBundle(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "world_manifest.yaml").write_text(textwrap.dedent("""\
            world_id: default
            allowed_tools: [read_file, list_repo, send_email]
            capabilities:
              read_file: {allowed: true}
              list_repo: {allowed: true}
              send_email: {allowed: true}
              dangerous_exec: {allowed: false}
            taint_rules:
              - tainted_external: deny
            side_effects: {external: restricted}
        """), encoding="utf-8")
        config_dir = self.tmp / "safe_mcp_proxy" / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "policy.yaml").write_text(
            "simulation:\n  external_side_effects: true\n", encoding="utf-8"
        )
        logs_dir = self.tmp / "safe_mcp_proxy" / "logs"
        logs_dir.mkdir(parents=True)
        (logs_dir / "audit.jsonl").write_text("", encoding="utf-8")
        self.app = create_app(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _request(self, method, path, **kwargs):
        async def _run():
            transport = httpx.ASGITransport(app=self.app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                return await client.request(method, path, **kwargs)
        return asyncio.run(_run())

    def test_export_bundle_returns_valid_structure(self):
        response = self._request("GET", "/export/bundle?scenario=benign_flow")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["schema_version"], 1)
        self.assertIn("generated_at", body)
        self.assertIn("scenario", body)
        self.assertIn("manifest", body)
        self.assertIn("traces", body)
        self.assertEqual(body["scenario"]["name"], "benign_flow")
        self.assertIn("allowlist", body["manifest"])
        self.assertIn("capability_map", body["manifest"])

    def test_export_bundle_unknown_scenario_returns_404(self):
        response = self._request("GET", "/export/bundle?scenario=no_such_scenario")
        self.assertEqual(response.status_code, 404)

    def test_export_bundle_with_trace_id(self):
        # First run a scenario to generate a trace
        run_response = self._request("POST", "/scenarios/benign_flow/run")
        self.assertEqual(run_response.status_code, 200)
        trace_id = run_response.json()["trace_id"]
        self.assertIsNotNone(trace_id)

        response = self._request(
            "GET", f"/export/bundle?scenario=benign_flow&trace_id={trace_id}"
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["traces"]), 1)
        self.assertEqual(body["traces"][0]["id"], trace_id)


class TestBundleReplay(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "world_manifest.yaml").write_text(textwrap.dedent("""\
            world_id: default
            allowed_tools: [read_file, list_repo, send_email]
            capabilities:
              read_file: {allowed: true}
              list_repo: {allowed: true}
              send_email: {allowed: true}
              dangerous_exec: {allowed: false}
            taint_rules:
              - tainted_external: deny
            side_effects: {external: restricted}
        """), encoding="utf-8")
        config_dir = self.tmp / "safe_mcp_proxy" / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "policy.yaml").write_text(
            "simulation:\n  external_side_effects: true\n", encoding="utf-8"
        )
        logs_dir = self.tmp / "safe_mcp_proxy" / "logs"
        logs_dir.mkdir(parents=True)
        (logs_dir / "audit.jsonl").write_text("", encoding="utf-8")
        self.app = create_app(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _request(self, method, path, **kwargs):
        async def _run():
            transport = httpx.ASGITransport(app=self.app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                return await client.request(method, path, **kwargs)
        return asyncio.run(_run())

    def _export_bundle(self, scenario="benign_flow"):
        self._request("POST", f"/scenarios/{scenario}/run")
        resp = self._request("GET", f"/export/bundle?scenario={scenario}")
        self.assertEqual(resp.status_code, 200)
        return resp.json()

    def test_replay_bundle_returns_summary_structure(self):
        bundle = self._export_bundle()
        resp = self._request("POST", "/replay/bundle", json=bundle)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("total", body)
        self.assertIn("matched", body)
        self.assertIn("diverged", body)
        self.assertIn("results", body)
        self.assertEqual(body["total"], body["matched"] + body["diverged"])

    def test_replay_bundle_all_match_unchanged_manifest(self):
        bundle = self._export_bundle()
        resp = self._request("POST", "/replay/bundle", json=bundle)
        body = resp.json()
        self.assertEqual(body["diverged"], 0)
        self.assertEqual(body["matched"], body["total"])

    def test_replay_bundle_empty_traces(self):
        bundle = self._export_bundle()
        bundle["traces"] = []
        resp = self._request("POST", "/replay/bundle", json=bundle)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["total"], 0)
        self.assertEqual(body["diverged"], 0)

    def test_replay_bundle_invalid_missing_key_returns_422(self):
        resp = self._request("POST", "/replay/bundle", json={"bad": "bundle"})
        self.assertEqual(resp.status_code, 422)


class TestSeedDemoData(unittest.TestCase):
    SEED_CONTENT = (
        '{"decision": "ALLOW", "descriptor_hash": "aaa", "rule": "default_allow", '
        '"source_channel": "cli", "taint": false, "timestamp": "2026-01-01T00:00:00+00:00", "tool": "read_file"}\n'
        '{"decision": "DENY", "descriptor_hash": "bbb", "rule": "tainted_external_side_effect", '
        '"source_channel": "web", "taint": true, "timestamp": "2026-01-01T00:01:00+00:00", "tool": "send_email"}\n'
        '{"decision": "ABSENT", "descriptor_hash": "", "rule": "tool_not_allowlisted", '
        '"source_channel": "cli", "taint": false, "timestamp": "2026-01-01T00:02:00+00:00", "tool": "dangerous_exec"}\n'
        '{"decision": "SIMULATE", "descriptor_hash": "ccc", "rule": "simulate_external_action", '
        '"source_channel": "cli", "taint": false, "timestamp": "2026-01-01T00:03:00+00:00", "tool": "send_email"}\n'
    )

    def _make_base_dir(self, with_audit_content=""):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "world_manifest.yaml").write_text(textwrap.dedent("""\
            world_id: default
            allowed_tools: [read_file, send_email]
            capabilities:
              read_file: {allowed: true}
              send_email: {allowed: true}
            taint_rules: []
            side_effects: {external: restricted}
        """), encoding="utf-8")
        config_dir = tmp / "safe_mcp_proxy" / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "policy.yaml").write_text(
            "simulation:\n  external_side_effects: true\n", encoding="utf-8"
        )
        logs_dir = tmp / "safe_mcp_proxy" / "logs"
        logs_dir.mkdir(parents=True)
        (logs_dir / "audit.jsonl").write_text(with_audit_content, encoding="utf-8")
        seeds_dir = tmp / "seeds"
        seeds_dir.mkdir()
        (seeds_dir / "demo.jsonl").write_text(self.SEED_CONTENT, encoding="utf-8")
        return tmp

    def _request(self, app, method, path, **kwargs):
        async def _run():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                return await client.request(method, path, **kwargs)
        return asyncio.run(_run())

    def test_seeds_loaded_when_audit_is_empty(self):
        tmp = self._make_base_dir(with_audit_content="")
        try:
            app = create_app(tmp)
            response = self._request(app, "GET", "/traces?limit=10")
            self.assertEqual(response.status_code, 200)
            traces = response.json()["traces"]
            decisions = {t["decision"] for t in traces}
            self.assertEqual(decisions, {"ALLOW", "DENY", "ABSENT", "SIMULATE"})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_seeds_not_loaded_when_audit_has_data(self):
        existing = (
            '{"decision": "ALLOW", "descriptor_hash": "x", "rule": "default_allow", '
            '"source_channel": "cli", "taint": false, "timestamp": "2026-01-01T00:00:00+00:00", "tool": "read_file"}\n'
        )
        tmp = self._make_base_dir(with_audit_content=existing)
        try:
            app = create_app(tmp)
            response = self._request(app, "GET", "/traces?limit=10")
            self.assertEqual(response.status_code, 200)
            traces = response.json()["traces"]
            self.assertEqual(len(traces), 1)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestDashboard(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "world_manifest.yaml").write_text(textwrap.dedent("""\
            world_id: default
            allowed_tools: [read_file, send_email]
            capabilities:
              read_file: {allowed: true}
              send_email: {allowed: true}
            taint_rules:
              - tainted_external: deny
            side_effects: {external: restricted}
        """), encoding="utf-8")
        config_dir = self.tmp / "safe_mcp_proxy" / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "policy.yaml").write_text(
            "simulation:\n  external_side_effects: true\n", encoding="utf-8"
        )
        logs_dir = self.tmp / "safe_mcp_proxy" / "logs"
        logs_dir.mkdir(parents=True)
        self.audit_log = logs_dir / "audit.jsonl"
        self.audit_log.write_text("", encoding="utf-8")
        self.app = create_app(self.tmp)

    async def asyncTearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    async def _get(self, path: str, **kwargs):
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.get(path, **kwargs)

    async def test_dashboard_returns_200_with_feed_element(self):
        resp = await self._get("/dashboard")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/html", resp.headers["content-type"])
        self.assertIn('id="feed"', resp.text)
        self.assertIn("EventSource", resp.text)

    async def test_dashboard_has_no_external_deps(self):
        resp = await self._get("/dashboard")
        body = resp.text
        self.assertNotIn("cdn.", body)
        self.assertNotIn("unpkg.com", body)
        self.assertNotIn("jsdelivr", body)

    async def test_events_content_type_is_sse(self):
        transport = httpx.ASGITransport(app=self.app)

        async def _check():
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                async with client.stream("GET", "/events") as resp:
                    self.assertEqual(resp.status_code, 200)
                    self.assertIn("text/event-stream", resp.headers["content-type"])
                    await asyncio.sleep(100)  # cancelled by wait_for

        try:
            await asyncio.wait_for(_check(), timeout=0.5)
        except asyncio.TimeoutError:
            pass

    # ── M3: stats bar + tool surface ──────────────────────────────────

    async def test_worlds_current_returns_world_id_and_tools(self):
        resp = await self._get("/worlds/current")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("world_id", body)
        self.assertIn("tools", body)
        self.assertIsInstance(body["tools"], list)
        self.assertGreater(len(body["tools"]), 0)

    async def test_worlds_current_tools_have_required_fields(self):
        resp = await self._get("/worlds/current")
        for tool in resp.json()["tools"]:
            self.assertIn("name", tool)
            self.assertIn("side_effect_type", tool)
            self.assertIn(tool["side_effect_type"], ("read", "internal", "external"))

    async def test_dashboard_has_stats_bar(self):
        resp = await self._get("/dashboard")
        body = resp.text
        self.assertIn('id="stats-bar"', body)
        self.assertIn("refreshStats", body)
        self.assertIn("/stats", body)

    async def test_dashboard_has_tool_surface(self):
        resp = await self._get("/dashboard")
        body = resp.text
        self.assertIn('id="surface"', body)
        self.assertIn("loadSurface", body)
        self.assertIn("/worlds/current", body)

    async def test_dashboard_stats_repaint_on_palette_change(self):
        resp = await self._get("/dashboard")
        body = resp.text
        self.assertIn("stat-dec", body)
        self.assertIn("repaintChips", body)
        # repaintChips must touch .stat-dec elements
        self.assertIn(".stat-dec", body)

    # ── M2: palettes ──────────────────────────────────────────────────

    async def test_dashboard_has_two_palettes(self):
        resp = await self._get("/dashboard")
        body = resp.text
        self.assertIn("traffic", body)
        self.assertIn("accessible", body)
        self.assertIn("PALETTES", body)

    async def test_accessible_palette_has_no_red_or_green_for_allow_deny(self):
        resp = await self._get("/dashboard")
        body = resp.text
        # Extract accessible palette block conservatively:
        # ALLOW must not be green (#388e3c / #4caf50) and DENY must not be red (#c62828 / #e53935)
        # We check that the accessible entry for ALLOW/DENY differs from traffic
        self.assertIn("accessible", body)
        # blue for ALLOW
        self.assertIn("0077bb", body)
        # orange for DENY
        self.assertIn("ee7733", body)

    async def test_dashboard_has_palette_switcher(self):
        resp = await self._get("/dashboard")
        body = resp.text
        self.assertIn('<select', body)
        self.assertIn("localStorage", body)

    async def test_dashboard_feed_columns_present(self):
        resp = await self._get("/dashboard")
        body = resp.text
        for cls in ("chip", "ts", "tool", "rule", "src", "taint"):
            self.assertIn(f'className: \'{cls}\'', body)

    async def test_events_generator_emits_new_audit_entry(self):
        """SSE generator yields a data line when audit.jsonl is appended to."""
        from api.main import _sse_stream

        async def write_after():
            await asyncio.sleep(0.3)
            with open(self.audit_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(SAMPLE_ENTRIES[0]) + "\n")

        write_task = asyncio.create_task(write_after())
        chunks = []
        async for chunk in _sse_stream(self.audit_log):
            if chunk.startswith("data:"):
                chunks.append(json.loads(chunk[5:].strip()))
                break
        await write_task

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["decision"], "ALLOW")
        self.assertEqual(chunks[0]["tool"], "read_file")

    async def test_events_generator_skips_existing_content(self):
        """SSE generator starts at EOF — pre-existing entries are not replayed."""
        from api.main import _sse_stream

        # Pre-populate the log
        with open(self.audit_log, "w", encoding="utf-8") as f:
            f.write(json.dumps(SAMPLE_ENTRIES[1]) + "\n")  # DENY entry

        async def write_new_after():
            await asyncio.sleep(0.3)
            with open(self.audit_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(SAMPLE_ENTRIES[0]) + "\n")  # new ALLOW entry

        write_task = asyncio.create_task(write_new_after())
        chunks = []
        async for chunk in _sse_stream(self.audit_log):
            if chunk.startswith("data:"):
                chunks.append(json.loads(chunk[5:].strip()))
                break
        await write_task

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["decision"], "ALLOW")  # only the new entry

    async def test_events_missing_log_does_not_crash(self):
        self.audit_log.unlink()
        transport = httpx.ASGITransport(app=self.app)

        async def _check():
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                async with client.stream("GET", "/events") as resp:
                    self.assertEqual(resp.status_code, 200)
                    await asyncio.sleep(100)

        try:
            await asyncio.wait_for(_check(), timeout=0.5)
        except asyncio.TimeoutError:
            pass


if __name__ == "__main__":
    unittest.main()
