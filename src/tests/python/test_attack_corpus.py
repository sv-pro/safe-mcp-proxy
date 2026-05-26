import unittest
from pathlib import Path

from attacks.loader import load, load_all, load_document, AttackScenario, ATTACKS_DIR

EXAMPLE = ATTACKS_DIR / "example.yaml"
EMAIL_INJECTION_YAML = ATTACKS_DIR / "email_injection.yaml"
EMAIL_INJECTION_MD   = ATTACKS_DIR / "email_injection.md"


class TestAttackLoader(unittest.TestCase):
    def test_example_loads(self):
        scenario = load(EXAMPLE)
        self.assertIsInstance(scenario, AttackScenario)

    def test_example_fields(self):
        s = load(EXAMPLE)
        self.assertEqual(s.name, "example_exfil")
        self.assertEqual(s.type, "email_injection")
        self.assertEqual(s.source_channel, "web")
        self.assertEqual(s.expected_baseline, "ALLOW")
        self.assertEqual(s.expected_protected, "DENY")

    def test_example_has_steps(self):
        s = load(EXAMPLE)
        self.assertGreater(len(s.steps), 0)
        tools = [step.tool for step in s.steps]
        self.assertIn("send_email", tools)

    def test_load_all_includes_example(self):
        scenarios = load_all(ATTACKS_DIR)
        names = [s.name for s in scenarios]
        self.assertIn("example_exfil", names)

    def test_load_all_skips_schema(self):
        scenarios = load_all(ATTACKS_DIR)
        names = [s.name for s in scenarios]
        self.assertNotIn("schema", names)

    def test_missing_field_raises(self):
        import tempfile, yaml, os
        bad = {"name": "x", "description": "y"}
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            yaml.dump(bad, f)
            tmp = Path(f.name)
        try:
            with self.assertRaises(ValueError):
                load(tmp)
        finally:
            os.unlink(tmp)

    def test_load_all_includes_email_injection(self):
        scenarios = load_all(ATTACKS_DIR)
        names = [s.name for s in scenarios]
        self.assertIn("email_injection", names)


class TestEmailInjectionScenario(unittest.TestCase):
    def test_yaml_loads(self):
        s = load(EMAIL_INJECTION_YAML)
        self.assertIsInstance(s, AttackScenario)
        self.assertEqual(s.name, "email_injection")

    def test_type_and_channel(self):
        s = load(EMAIL_INJECTION_YAML)
        self.assertEqual(s.type, "email_injection")
        self.assertEqual(s.source_channel, "web")

    def test_expected_decisions(self):
        s = load(EMAIL_INJECTION_YAML)
        self.assertEqual(s.expected_baseline, "ALLOW")
        self.assertEqual(s.expected_protected, "DENY")

    def test_steps_include_send_email(self):
        s = load(EMAIL_INJECTION_YAML)
        tools = [step.tool for step in s.steps]
        self.assertIn("send_email", tools)

    def test_document_is_loaded(self):
        s = load(EMAIL_INJECTION_YAML)
        self.assertTrue(s.document, "document field should be non-empty")

    def test_document_contains_hidden_instruction(self):
        doc = load_document(EMAIL_INJECTION_MD)
        self.assertIn("send_email", doc)
        self.assertIn("SYSTEM", doc)

    def test_document_looks_legitimate(self):
        doc = load_document(EMAIL_INJECTION_MD)
        # Should read as a normal business document on the surface
        self.assertIn("Q1", doc)
        self.assertIn("Operations", doc)

    def test_md_file_exists(self):
        self.assertTrue(EMAIL_INJECTION_MD.exists())


    def test_invalid_type_raises(self):
        import tempfile, yaml, os
        bad = {
            "name": "x", "description": "y", "type": "unknown",
            "source_channel": "web", "steps": [],
            "expected": {"baseline": "ALLOW", "protected": "DENY"},
        }
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            yaml.dump(bad, f)
            tmp = Path(f.name)
        try:
            with self.assertRaises(ValueError):
                load(tmp)
        finally:
            os.unlink(tmp)
