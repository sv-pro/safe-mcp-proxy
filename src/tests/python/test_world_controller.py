"""Tests for WorldController: thread safety, switch diffs, tool visibility, API integration."""

import asyncio
import json
import shutil
import tempfile
import textwrap
import threading
import unittest
from pathlib import Path

from safe_mcp_proxy.executor import Executor
from safe_mcp_proxy.policy_engine import PolicyEngine
from safe_mcp_proxy.registry import ToolRegistry
from safe_mcp_proxy.world_controller import WorldController, WorldNotFoundError

try:
    import fastapi  # noqa: F401
    import httpx    # noqa: F401
    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False


# ---------------------------------------------------------------------------
# Shared fixture helpers
# ---------------------------------------------------------------------------

def _make_tmp() -> Path:
    tmp = Path(tempfile.mkdtemp())
    # Default world manifest
    (tmp / "world_manifest.yaml").write_text(textwrap.dedent("""\
        world_id: default
        allowed_tools: [read_file, list_repo, send_email]
        capabilities:
          read_file: {allowed: true}
          list_repo: {allowed: true}
          send_email: {allowed: true}
          dangerous_exec: {allowed: false}
        taint_rules: []
        side_effects: {external: restricted}
    """), encoding="utf-8")
    # read_only world
    worlds_dir = tmp / "worlds"
    worlds_dir.mkdir()
    (worlds_dir / "read_only.yaml").write_text(textwrap.dedent("""\
        world_id: read_only
        allowed_tools: [read_file]
        capabilities:
          read_file: {allowed: true}
          list_repo: {allowed: false}
          send_email: {allowed: false}
          dangerous_exec: {allowed: false}
        taint_rules: []
        side_effects: {external: restricted}
    """), encoding="utf-8")
    # Stub policy.yaml (needed by build_executor's _load_simulation_flag)
    config_dir = tmp / "safe_mcp_proxy" / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "policy.yaml").write_text("simulation:\n  external_side_effects: true\n")
    # Stub logs dir
    (tmp / "safe_mcp_proxy" / "logs").mkdir(parents=True)
    return tmp


# ---------------------------------------------------------------------------
# Unit tests for WorldController
# ---------------------------------------------------------------------------

class TestWorldControllerSwitch(unittest.TestCase):
    def setUp(self):
        self.tmp = _make_tmp()
        self.controller = WorldController(initial_world_id="", base_dir=self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_switch_returns_correct_diff(self):
        diff = self.controller.switch("read_only")
        self.assertEqual(diff["from"], "")
        self.assertEqual(diff["to"], "read_only")
        self.assertIn("list_repo", diff["vanished"])
        self.assertIn("send_email", diff["vanished"])
        self.assertNotIn("read_file", diff["vanished"])
        self.assertNotIn("read_file", diff["appeared"])

    def test_switch_reason_preserved(self):
        diff = self.controller.switch("read_only", reason="testing")
        self.assertEqual(diff["reason"], "testing")

    def test_history_records_switch_order(self):
        self.controller.switch("read_only")
        self.controller.switch("")
        history = self.controller.history
        self.assertEqual(history[0], "")       # initial
        self.assertEqual(history[1], "read_only")
        self.assertEqual(history[2], "")

    def test_current_id_reflects_latest_switch(self):
        self.assertEqual(self.controller.current_id(), "")
        self.controller.switch("read_only")
        self.assertEqual(self.controller.current_id(), "read_only")

    def test_world_not_found_error_for_missing_world(self):
        with self.assertRaises(WorldNotFoundError):
            self.controller.switch("nonexistent_world_xyz")

    def test_world_not_found_does_not_corrupt_state(self):
        try:
            self.controller.switch("nonexistent_world_xyz")
        except WorldNotFoundError:
            pass
        # Current world unchanged
        self.assertEqual(self.controller.current_id(), "")
        self.assertIn("send_email", {t["name"] for t in self.controller.list_tools()})


class TestWorldControllerListTools(unittest.TestCase):
    def setUp(self):
        self.tmp = _make_tmp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_list_tools_reflects_new_world_immediately(self):
        controller = WorldController(initial_world_id="", base_dir=self.tmp)
        default_tools = {t["name"] for t in controller.list_tools()}
        self.assertIn("send_email", default_tools)
        self.assertIn("list_repo", default_tools)

        controller.switch("read_only")

        readonly_tools = {t["name"] for t in controller.list_tools()}
        self.assertIn("read_file", readonly_tools)
        self.assertNotIn("send_email", readonly_tools)
        self.assertNotIn("list_repo", readonly_tools)
        self.assertGreater(len(default_tools), len(readonly_tools))

    def test_list_tools_returns_required_keys(self):
        controller = WorldController(initial_world_id="", base_dir=self.tmp)
        for tool in controller.list_tools():
            self.assertIn("name", tool)
            self.assertIn("capability", tool)
            self.assertIn("side_effect_type", tool)


class TestWorldControllerConcurrency(unittest.TestCase):
    def setUp(self):
        self.tmp = _make_tmp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_concurrent_switch_and_read_do_not_race(self):
        controller = WorldController(initial_world_id="", base_dir=self.tmp)
        errors: list = []
        n_readers = 2
        barrier = threading.Barrier(n_readers + 1)  # readers + 1 switcher

        def reader():
            barrier.wait()
            for _ in range(100):
                try:
                    _ = controller.world
                    _ = controller.current_id()
                except Exception as exc:
                    errors.append(exc)

        def switcher():
            barrier.wait()
            for _ in range(20):
                try:
                    controller.switch("read_only")
                    controller.switch("")
                except WorldNotFoundError as exc:
                    errors.append(exc)

        threads = [threading.Thread(target=reader) for _ in range(n_readers)]
        threads.append(threading.Thread(target=switcher))
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertFalse(errors, f"Concurrency errors: {errors}")


# ---------------------------------------------------------------------------
# replay() fallback for entries without world_id
# ---------------------------------------------------------------------------

class TestReplayWorldIdFallback(unittest.TestCase):
    def setUp(self):
        self.tmp = _make_tmp()
        self.audit_file = self.tmp / "safe_mcp_proxy" / "logs" / "audit.jsonl"
        registry = ToolRegistry.with_mock_tools(
            allowlist=["read_file"],
        )
        policy = PolicyEngine(
            allowlist=["read_file"],
            capability_map={"read_file": True},
            approval_required=[],
        )
        self.executor = Executor(
            registry=registry,
            policy_engine=policy,
            audit_log_path=str(self.audit_file),
            simulate_external=True,
        )

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_replay_without_world_id_does_not_raise(self):
        entry = {
            "tool": "read_file",
            "taint": False,
            "decision": "ALLOW",
            "rule": "default_allow",
            # no "world_id" key — simulates old seed entries
        }
        result = self.executor.replay(entry)
        self.assertIn("matches", result)
        self.assertIn("replayed_decision", result)

    def test_replay_with_world_id_present_does_not_raise(self):
        entry = {
            "tool": "read_file",
            "taint": False,
            "decision": "ALLOW",
            "rule": "default_allow",
            "world_id": "default",
        }
        result = self.executor.replay(entry)
        self.assertIn("matches", result)


# ---------------------------------------------------------------------------
# audit.jsonl contains WORLD_SWITCH event after API call
# ---------------------------------------------------------------------------

@unittest.skipUnless(_FASTAPI_AVAILABLE, "fastapi/httpx not installed")
class TestWorldSwitchAPIEndpoints(unittest.TestCase):
    def setUp(self):
        from api.main import create_app

        self.tmp = _make_tmp()
        self.audit_log = self.tmp / "safe_mcp_proxy" / "logs" / "audit.jsonl"
        self.audit_log.touch()

        # Add read_only world via safe_mcp_proxy/config/worlds/ so build_executor finds it
        config_worlds = self.tmp / "safe_mcp_proxy" / "config" / "worlds"
        config_worlds.mkdir(parents=True, exist_ok=True)
        (config_worlds / "read_only.yaml").write_text(textwrap.dedent("""\
            world_id: read_only
            allowed_tools: [read_file]
            capabilities:
              read_file: {allowed: true}
              list_repo: {allowed: false}
              send_email: {allowed: false}
              dangerous_exec: {allowed: false}
            taint_rules: []
            side_effects: {external: restricted}
        """), encoding="utf-8")

        self.app = create_app(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _request(self, method: str, path: str, **kwargs):
        import httpx
        async def _run():
            transport = httpx.ASGITransport(app=self.app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                return await client.request(method, path, **kwargs)
        return asyncio.run(_run())

    def test_post_world_switch_returns_diff(self):
        resp = self._request("POST", "/world/switch", params={"world_id": "read_only"})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["to"], "read_only")
        self.assertIn("appeared", body)
        self.assertIn("vanished", body)

    def test_post_world_switch_unknown_returns_404(self):
        resp = self._request("POST", "/world/switch", params={"world_id": "no_such_world"})
        self.assertEqual(resp.status_code, 404)

    def test_get_world_current_reflects_switch(self):
        self._request("POST", "/world/switch", params={"world_id": "read_only"})
        resp = self._request("GET", "/world/current")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["world_id"], "read_only")
        self.assertIn("history", body)
        self.assertIn("read_only", body["history"])

    def test_world_switch_appends_audit_event(self):
        self._request("POST", "/world/switch", params={"world_id": "read_only", "reason": "test"})
        lines = [l for l in self.audit_log.read_text().splitlines() if l.strip()]
        events = [json.loads(l) for l in lines]
        switch_events = [e for e in events if e.get("event") == "WORLD_SWITCH"]
        self.assertEqual(len(switch_events), 1)
        evt = switch_events[0]
        self.assertIn("diff", evt)
        self.assertIn("timestamp", evt)
        self.assertEqual(evt["diff"]["to"], "read_only")

    def test_worlds_current_reflects_switch(self):
        """Existing /worlds/current endpoint still returns correct tools after switch."""
        self._request("POST", "/world/switch", params={"world_id": "read_only"})
        resp = self._request("GET", "/worlds/current")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        tool_names = {t["name"] for t in body["tools"]}
        self.assertIn("read_file", tool_names)
        self.assertNotIn("send_email", tool_names)

    def test_execute_reflects_switched_world(self):
        """After switching to read_only, send_email should be ABSENT."""
        from safe_mcp_proxy.main import build_executor
        from safe_mcp_proxy.provenance import Provenance

        executor = build_executor(self.tmp)
        executor.world_controller.switch("read_only")  # type: ignore[union-attr]
        prov = Provenance.from_source("cli")
        result = executor.execute("send_email", {}, prov)
        self.assertEqual(result["decision"], "ABSENT")


if __name__ == "__main__":
    unittest.main()
