import json
import shutil
import tempfile
import unittest
import asyncio
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


if __name__ == "__main__":
    unittest.main()
