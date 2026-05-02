"""Tests for EPIC 8 Issue #88 — Gemini proxy passthrough endpoint."""
import asyncio
import shutil
import tempfile
import textwrap
import unittest
from pathlib import Path

import httpx

from api.main import create_app


_MANIFEST = textwrap.dedent("""\
    world_id: default
    allowed_tools: [read_file, send_email]
    capabilities:
      read_file: {allowed: true}
      send_email: {allowed: true}
    taint_rules:
      - tainted_external: deny
    side_effects: {external: restricted}
""")

_POLICY = "simulation:\n  external_side_effects: true\n"


class GeminiProxyEndpointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "world_manifest.yaml").write_text(_MANIFEST, encoding="utf-8")
        config_dir = self.tmp / "safe_mcp_proxy" / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "policy.yaml").write_text(_POLICY, encoding="utf-8")
        logs_dir = self.tmp / "safe_mcp_proxy" / "logs"
        logs_dir.mkdir(parents=True)
        (logs_dir / "audit.jsonl").write_text("", encoding="utf-8")
        self.app = create_app(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _post(self, payload: dict) -> httpx.Response:
        async def _run():
            transport = httpx.ASGITransport(app=self.app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                return await client.post("/integrations/gemini/tools/execute", json=payload)
        return asyncio.run(_run())

    # ------------------------------------------------------------------
    # Happy path
    # ------------------------------------------------------------------

    def test_clean_read_file_is_allowed(self):
        payload = {
            "functionCall": {"name": "read_file", "args": {"path": "README.md"}},
            "metadata": {"source_channel": "cli"},
        }
        resp = self._post(payload)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("functionResponse", body)
        self.assertEqual(body["functionResponse"]["name"], "read_file")
        self.assertEqual(body["functionResponse"]["response"]["decision"], "ALLOW")

    def test_response_is_gemini_function_response_envelope(self):
        payload = {"functionCall": {"name": "read_file", "args": {}}}
        resp = self._post(payload)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("functionResponse", body)
        self.assertIn("name", body["functionResponse"])
        self.assertIn("response", body["functionResponse"])

    # ------------------------------------------------------------------
    # Policy enforcement via executor
    # ------------------------------------------------------------------

    def test_tainted_send_email_is_denied(self):
        payload = {
            "functionCall": {"name": "send_email", "args": {"to": "x@example.com", "body": "hi"}},
            "metadata": {"source_channel": "web"},
        }
        resp = self._post(payload)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["functionResponse"]["response"]["decision"], "DENY")
        self.assertEqual(
            body["functionResponse"]["response"]["rule"],
            "tainted_external_side_effect",
        )

    def test_unknown_tool_returns_absent(self):
        payload = {"functionCall": {"name": "exfiltrate_everything", "args": {}}}
        resp = self._post(payload)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["functionResponse"]["response"]["decision"], "ABSENT")

    def test_source_channel_defaults_to_web_when_omitted(self):
        # send_email without metadata → defaults to web (tainted) → DENY
        payload = {
            "functionCall": {"name": "send_email", "args": {"to": "x@example.com", "body": "hi"}},
        }
        resp = self._post(payload)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.json()["functionResponse"]["response"]["decision"], "DENY"
        )

    # ------------------------------------------------------------------
    # Malformed requests → 422
    # ------------------------------------------------------------------

    def test_missing_function_call_returns_422(self):
        resp = self._post({"something": "else"})
        self.assertEqual(resp.status_code, 422)

    def test_missing_tool_name_returns_422(self):
        resp = self._post({"functionCall": {"args": {"path": "README.md"}}})
        self.assertEqual(resp.status_code, 422)

    def test_non_dict_body_returns_422(self):
        async def _run():
            transport = httpx.ASGITransport(app=self.app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                return await client.post(
                    "/integrations/gemini/tools/execute",
                    content=b'"just a string"',
                    headers={"content-type": "application/json"},
                )
        resp = asyncio.run(_run())
        self.assertEqual(resp.status_code, 422)

    # ------------------------------------------------------------------
    # Audit logging
    # ------------------------------------------------------------------

    def test_request_is_logged_to_audit_file(self):
        payload = {
            "functionCall": {"name": "read_file", "args": {}},
            "metadata": {"source_channel": "cli"},
        }
        self._post(payload)
        audit = (self.tmp / "safe_mcp_proxy" / "logs" / "audit.jsonl").read_text(encoding="utf-8")
        self.assertIn("read_file", audit)
        self.assertIn("ALLOW", audit)


class GeminiToolsListEndpointTests(unittest.TestCase):
    """Tests for GET /integrations/gemini/tools/list (Issue #89)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        # Only read_file and list_repo allowed — send_email is absent
        (self.tmp / "world_manifest.yaml").write_text(textwrap.dedent("""\
            world_id: default
            allowed_tools: [read_file, list_repo]
            capabilities:
              read_file: {allowed: true}
              list_repo: {allowed: true}
              send_email: {allowed: false}
            taint_rules:
              - tainted_external: deny
            side_effects: {external: restricted}
        """), encoding="utf-8")
        config_dir = self.tmp / "safe_mcp_proxy" / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "policy.yaml").write_text(_POLICY, encoding="utf-8")
        logs_dir = self.tmp / "safe_mcp_proxy" / "logs"
        logs_dir.mkdir(parents=True)
        (logs_dir / "audit.jsonl").write_text("", encoding="utf-8")
        self.app = create_app(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _get(self) -> httpx.Response:
        async def _run():
            transport = httpx.ASGITransport(app=self.app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                return await client.get("/integrations/gemini/tools/list")
        return asyncio.run(_run())

    def test_returns_200(self):
        self.assertEqual(self._get().status_code, 200)

    def test_response_has_tools_key(self):
        body = self._get().json()
        self.assertIn("tools", body)
        self.assertIsInstance(body["tools"], list)

    def test_only_allowlisted_tools_are_returned(self):
        names = {t["name"] for t in self._get().json()["tools"]}
        self.assertIn("read_file", names)
        self.assertIn("list_repo", names)

    def test_absent_tool_is_not_in_list(self):
        names = {t["name"] for t in self._get().json()["tools"]}
        self.assertNotIn("send_email", names)
        self.assertNotIn("dangerous_exec", names)

    def test_each_tool_has_name_and_parameters(self):
        for tool in self._get().json()["tools"]:
            self.assertIn("name", tool)
            self.assertIn("parameters", tool)

    def test_parameters_is_json_schema_object(self):
        for tool in self._get().json()["tools"]:
            params = tool["parameters"]
            self.assertEqual(params.get("type"), "object")
            self.assertIn("properties", params)


if __name__ == "__main__":
    unittest.main()
