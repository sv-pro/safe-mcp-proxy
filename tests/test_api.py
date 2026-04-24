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


if __name__ == "__main__":
    unittest.main()
