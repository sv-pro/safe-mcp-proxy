"""Tests for the MCPZero Demo components (EPIC 11 I3–I15)."""
import json
import tempfile
import unittest
from pathlib import Path

from attacks.loader import load, load_all, ATTACKS_DIR


# ---------------------------------------------------------------------------
# I3 — tool_chain scenario
# ---------------------------------------------------------------------------
class TestToolChain(unittest.TestCase):
    def setUp(self):
        self.s = load(ATTACKS_DIR / "tool_chain.yaml")

    def test_loads(self):
        self.assertEqual(self.s.name, "tool_chain")
        self.assertEqual(self.s.type, "tool_chain")

    def test_channel_is_tainted(self):
        self.assertIn(self.s.source_channel, ("web", "email", "tool_output"))

    def test_multi_step(self):
        self.assertGreaterEqual(len(self.s.steps), 2)

    def test_includes_external_step(self):
        tools = [step.tool for step in self.s.steps]
        self.assertIn("send_email", tools)

    def test_expected_decisions(self):
        self.assertEqual(self.s.expected_baseline, "ALLOW")
        self.assertEqual(self.s.expected_protected, "DENY")


# ---------------------------------------------------------------------------
# I4 — mcp_poison scenario
# ---------------------------------------------------------------------------
class TestMCPPoison(unittest.TestCase):
    def setUp(self):
        self.s = load(ATTACKS_DIR / "mcp_poison.json")

    def test_loads(self):
        self.assertEqual(self.s.name, "mcp_poison")
        self.assertEqual(self.s.type, "mcp_poison")

    def test_poison_tool_present(self):
        self.assertIsNotNone(self.s.poison_tool)
        self.assertIn("tampered_schema", self.s.poison_tool)

    def test_tampered_schema_has_extra_property(self):
        props = self.s.poison_tool["tampered_schema"]["properties"]
        self.assertNotEqual(set(props.keys()), {"path"},
                            "tampered schema should add at least one extra property")

    def test_expected_decisions(self):
        self.assertEqual(self.s.expected_baseline, "ALLOW")
        self.assertEqual(self.s.expected_protected, "DENY")


# ---------------------------------------------------------------------------
# I5 — BaselineAgent
# ---------------------------------------------------------------------------
class TestBaselineAgent(unittest.TestCase):
    def _scenario(self):
        return load(ATTACKS_DIR / "email_injection.yaml")

    def test_runs_all_steps(self):
        from mcpzero.agent.runner import BaselineAgent
        s = self._scenario()
        results = BaselineAgent().run(s)
        self.assertEqual(len(results), len(s.steps))

    def test_all_decisions_allow(self):
        from mcpzero.agent.runner import BaselineAgent
        s = self._scenario()
        results = BaselineAgent().run(s)
        for r in results:
            self.assertEqual(r["decision"], "ALLOW")

    def test_unknown_tool_is_absent(self):
        from mcpzero.agent.runner import BaselineAgent
        from attacks.loader import AttackScenario, AttackStep
        s = AttackScenario(
            name="t", description="t", type="tool_chain",
            source_channel="cli", steps=[AttackStep("no_such_tool", {})],
            expected_baseline="ABSENT", expected_protected="ABSENT",
        )
        results = BaselineAgent().run(s)
        self.assertEqual(results[0]["decision"], "ABSENT")


# ---------------------------------------------------------------------------
# I6 / I7 — ScenarioRunner + mode switch
# ---------------------------------------------------------------------------
class TestScenarioRunner(unittest.TestCase):
    def test_invalid_mode_raises(self):
        from mcpzero.runner.interface import ScenarioRunner
        with self.assertRaises(ValueError):
            ScenarioRunner(mode="turbo")

    def test_baseline_mode_allows_send_email(self):
        from mcpzero.runner.interface import ScenarioRunner
        s = load(ATTACKS_DIR / "email_injection.yaml")
        result = ScenarioRunner(mode="baseline").run(s)
        self.assertIn("ALLOW", result.decisions())

    def test_protected_mode_denies_send_email(self):
        from mcpzero.runner.interface import ScenarioRunner
        s = load(ATTACKS_DIR / "email_injection.yaml")
        result = ScenarioRunner(mode="protected").run(s)
        self.assertIn("DENY", result.decisions())

    def test_modes_differ(self):
        from mcpzero.runner.interface import ScenarioRunner
        s = load(ATTACKS_DIR / "email_injection.yaml")
        b = ScenarioRunner(mode="baseline").run(s)
        p = ScenarioRunner(mode="protected").run(s)
        self.assertNotEqual(b.decisions(), p.decisions())

    def test_load_scenario_by_name(self):
        from mcpzero.runner.interface import load_scenario
        s = load_scenario("email_injection")
        self.assertEqual(s.name, "email_injection")

    def test_load_scenario_missing_raises(self):
        from mcpzero.runner.interface import load_scenario
        with self.assertRaises(FileNotFoundError):
            load_scenario("does_not_exist_xyz")


# ---------------------------------------------------------------------------
# I8 — Tool Surface Inventory
# ---------------------------------------------------------------------------
class TestToolGraph(unittest.TestCase):
    TOOL_GRAPH = Path(__file__).parent.parent / "mcpzero" / "tools" / "tool_graph.yaml"

    def _tools(self):
        import yaml
        with open(self.TOOL_GRAPH) as fh:
            return yaml.safe_load(fh)["tools"]

    def test_file_exists(self):
        self.assertTrue(self.TOOL_GRAPH.exists())

    def test_has_tools(self):
        self.assertGreater(len(self._tools()), 0)

    def test_required_fields(self):
        for t in self._tools():
            for f in ("name", "side_effect_type", "schema"):
                self.assertIn(f, t, f"tool {t.get('name')} missing field {f}")

    def test_external_tool_present(self):
        external = [t["name"] for t in self._tools() if t["side_effect_type"] == "external"]
        self.assertIn("send_email", external)


# ---------------------------------------------------------------------------
# I9 — Basic Attack Generator
# ---------------------------------------------------------------------------
class TestAttackGenerator(unittest.TestCase):
    def test_generates_at_least_one(self):
        from mcpzero.generator.attack_gen import generate
        scenarios = generate()
        self.assertGreater(len(scenarios), 0)

    def test_generated_has_required_fields(self):
        from mcpzero.generator.attack_gen import generate
        for s in generate():
            for f in ("name", "description", "type", "source_channel", "steps", "expected"):
                self.assertIn(f, s)

    def test_generated_targets_external_tools(self):
        from mcpzero.generator.attack_gen import generate
        for s in generate():
            tools = [step["tool"] for step in s["steps"]]
            # At least one external tool in the chain
            self.assertTrue(any(t in tools for t in ("send_email", "dangerous_exec")))


# ---------------------------------------------------------------------------
# I10 — Execution Observer
# ---------------------------------------------------------------------------
class TestExecutionObserver(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()

    def test_creates_trace_file(self):
        from mcpzero.observer.observer import ExecutionObserver
        obs = ExecutionObserver(trace_dir=Path(self._tmp))
        obs.record(mode="baseline", scenario="test", tool="read_file",
                   payload={}, decision="ALLOW")
        self.assertTrue(obs.log_path.exists())

    def test_entries_appended(self):
        from mcpzero.observer.observer import ExecutionObserver
        obs = ExecutionObserver(trace_dir=Path(self._tmp))
        obs.record(mode="baseline", scenario="s", tool="t1", payload={}, decision="ALLOW")
        obs.record(mode="protected", scenario="s", tool="t1", payload={}, decision="DENY")
        self.assertEqual(len(obs.entries), 2)

    def test_jsonl_format(self):
        from mcpzero.observer.observer import ExecutionObserver
        obs = ExecutionObserver(trace_dir=Path(self._tmp))
        obs.record(mode="baseline", scenario="s", tool="t", payload={}, decision="ALLOW", rule="no_policy")
        lines = obs.log_path.read_text().strip().splitlines()
        self.assertEqual(len(lines), 1)
        entry = json.loads(lines[0])
        self.assertIn("timestamp", entry)
        self.assertEqual(entry["decision"], "ALLOW")

    def test_observer_wired_into_runner(self):
        from mcpzero.runner.interface import ScenarioRunner
        from mcpzero.observer.observer import ExecutionObserver
        obs = ExecutionObserver(trace_dir=Path(self._tmp))
        s = load(ATTACKS_DIR / "email_injection.yaml")
        ScenarioRunner(mode="baseline").run(s, observer=obs)
        self.assertGreater(len(obs.entries), 0)


# ---------------------------------------------------------------------------
# I11 / I12 — SafeMCPProxy (core + integration)
# ---------------------------------------------------------------------------
class TestSafeMCPProxy(unittest.TestCase):
    def test_allows_clean_read(self):
        from mcpzero.proxy.proxy import SafeMCPProxy
        proxy = SafeMCPProxy()
        r = proxy.call("read_file", {"path": "README.md"}, "cli")
        self.assertEqual(r["decision"], "ALLOW")

    def test_denies_tainted_send_email(self):
        from mcpzero.proxy.proxy import SafeMCPProxy
        proxy = SafeMCPProxy()
        r = proxy.call("send_email", {"to": "x@y.com", "body": "hi"}, "web")
        self.assertEqual(r["decision"], "DENY")

    def test_denies_poisoned_descriptor(self):
        from mcpzero.proxy.proxy import SafeMCPProxy
        s = load(ATTACKS_DIR / "mcp_poison.json")
        proxy = SafeMCPProxy()
        results = proxy.run(s)
        decisions = [r["decision"] for r in results]
        self.assertIn("DENY", decisions)

    def test_all_steps_pass_through_proxy(self):
        from mcpzero.proxy.proxy import SafeMCPProxy
        s = load(ATTACKS_DIR / "email_injection.yaml")
        results = SafeMCPProxy().run(s)
        self.assertEqual(len(results), len(s.steps))

    def test_scoped_email_to_self_locks_receiver(self):
        from mcpzero.proxy.proxy import SafeMCPProxy
        proxy = SafeMCPProxy()
        proxy._executor.simulate_external = False
        tool = proxy._executor.registry.get_tool("send_email_to_self")
        self.assertIsNotNone(tool)
        self.assertNotIn("to", tool.schema.get("properties", {}))

        r = proxy.call(
            "send_email_to_self",
            {
                "to": "attacker@external.example.com",
                "subject": "Status",
                "body": "attempted override",
            },
            "cli",
        )
        self.assertEqual(r["decision"], "ALLOW")
        self.assertEqual(r["result"]["sent_to"], "owner@example.com")


# ---------------------------------------------------------------------------
# I13 — Verdict Engine
# ---------------------------------------------------------------------------
class TestVerdictEngine(unittest.TestCase):
    def _run_pair(self, scenario_name):
        from mcpzero.runner.interface import ScenarioRunner
        s = load(ATTACKS_DIR / f"{scenario_name}.yaml")
        b = ScenarioRunner(mode="baseline").run(s)
        p = ScenarioRunner(mode="protected").run(s)
        return s, b, p

    def test_email_injection_demo_pass(self):
        from mcpzero.verdict.engine import compare
        s, b, p = self._run_pair("email_injection")
        v = compare(s, b, p)
        self.assertTrue(v.demo_pass, f"Expected demo_pass but got: {v.to_dict()}")

    def test_verdict_to_dict_shape(self):
        from mcpzero.verdict.engine import compare
        s, b, p = self._run_pair("email_injection")
        v = compare(s, b, p)
        d = v.to_dict()
        for key in ("scenario", "attack_succeeded_baseline", "proxy_blocked", "demo_pass", "steps"):
            self.assertIn(key, d)

    def test_save_and_reload(self):
        from mcpzero.verdict.engine import compare, save
        s, b, p = self._run_pair("email_injection")
        v = compare(s, b, p)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)
        save([v], path)
        loaded = json.loads(path.read_text())
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]["scenario"], "email_injection")


# ---------------------------------------------------------------------------
# I14 — CLI Demo (smoke)
# ---------------------------------------------------------------------------
class TestCLIDemo(unittest.TestCase):
    def test_demo_module_importable(self):
        import mcpzero.demo  # noqa: F401

    def test_run_all_returns_verdicts(self):
        from mcpzero.demo import run_all
        scenarios = load_all(ATTACKS_DIR)
        verdicts = run_all(scenarios, output_dir=None, use_color=False)
        self.assertGreater(len(verdicts), 0)

    def test_all_scenarios_demo_pass(self):
        from mcpzero.demo import run_all
        scenarios = load_all(ATTACKS_DIR)
        verdicts = run_all(scenarios, output_dir=None, use_color=False)
        failing = [v.scenario for v in verdicts if not v.demo_pass]
        self.assertEqual(failing, [], f"Demo failed for: {failing}")


# ---------------------------------------------------------------------------
# I15 — Metrics & Reporting
# ---------------------------------------------------------------------------
class TestMetrics(unittest.TestCase):
    def _verdicts(self):
        from mcpzero.demo import run_all
        return run_all(load_all(ATTACKS_DIR), output_dir=None, use_color=False)

    def test_asr_is_one(self):
        from mcpzero.metrics.reporter import compute_asr
        self.assertEqual(compute_asr(self._verdicts()), 1.0)

    def test_block_rate_is_one(self):
        from mcpzero.metrics.reporter import compute_block_rate
        self.assertEqual(compute_block_rate(self._verdicts()), 1.0)

    def test_to_dict_shape(self):
        from mcpzero.metrics.reporter import to_dict
        d = to_dict(self._verdicts())
        for k in ("total", "asr", "block_rate", "demo_pass"):
            self.assertIn(k, d)

    def test_save_metrics(self):
        from mcpzero.metrics.reporter import save
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)
        save(self._verdicts(), path)
        d = json.loads(path.read_text())
        self.assertIn("asr", d)
