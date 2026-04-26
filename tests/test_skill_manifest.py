import os
import tempfile
import textwrap
import unittest

from safe_mcp_proxy.compiler import (
    SkillCapabilityConfig,
    SkillSourceConfig,
    compile_world_manifest,
    parse_skill_capabilities,
    parse_skill_sources,
)


def _write_manifest(content: str) -> str:
    """Write manifest YAML to a temp file and return its path."""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    f.write(textwrap.dedent(content))
    f.close()
    return f.name


class TestParseSkillSources(unittest.TestCase):

    def test_local_source(self):
        raw = {
            "local_skills": {
                "type": "local",
                "path": "/mock/skills",
                "trust_level": "internal",
                "import_mode": "explicit_only",
            }
        }
        result = parse_skill_sources(raw)
        self.assertIn("local_skills", result)
        src = result["local_skills"]
        self.assertEqual(src.source_type, "local")
        self.assertEqual(src.path, "/mock/skills")
        self.assertEqual(src.trust_level, "internal")

    def test_git_source(self):
        raw = {
            "google_skills_repo": {
                "type": "git",
                "url": "https://github.com/google/skills",
                "trust_level": "external_verified_source",
                "import_mode": "explicit_only",
            }
        }
        result = parse_skill_sources(raw)
        src = result["google_skills_repo"]
        self.assertEqual(src.source_type, "git")
        self.assertEqual(src.url, "https://github.com/google/skills")

    def test_defaults(self):
        result = parse_skill_sources({"src": {"type": "local"}})
        src = result["src"]
        self.assertEqual(src.trust_level, "external_unverified")
        self.assertEqual(src.import_mode, "explicit_only")

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            parse_skill_sources({"bad": "not-a-dict"})

    def test_empty_returns_empty(self):
        self.assertEqual(parse_skill_sources({}), {})


class TestParseSkillCapabilities(unittest.TestCase):

    def _sources(self):
        return parse_skill_sources({
            "google_skills_repo": {"type": "git", "url": "https://example.com"},
            "local_skills": {"type": "local", "path": "/tmp"},
        })

    def test_basic_skill_capability(self):
        raw = {
            "gcp.bigquery.read_dataset": {
                "source_skill": "google_skills_repo:bigquery",
                "exposed_as": "bigquery.read_dataset",
                "allowed": True,
                "side_effect": "none",
            }
        }
        result = parse_skill_capabilities(raw, self._sources())
        cap = result["gcp.bigquery.read_dataset"]
        self.assertEqual(cap.source_skill, "google_skills_repo:bigquery")
        self.assertEqual(cap.exposed_as, "bigquery.read_dataset")
        self.assertTrue(cap.allowed)
        self.assertEqual(cap.side_effect, "none")

    def test_conditional_allowed(self):
        raw = {
            "gcp.bigquery.run_query": {
                "source_skill": "google_skills_repo:bigquery",
                "exposed_as": "bigquery.run_query",
                "allowed": "conditional",
                "side_effect": "bounded_compute",
                "requires_approval": True,
                "constraints": {"max_bytes_billed": 100000000},
            }
        }
        result = parse_skill_capabilities(raw, self._sources())
        cap = result["gcp.bigquery.run_query"]
        self.assertEqual(cap.allowed, "conditional")
        self.assertTrue(cap.requires_approval)
        self.assertEqual(cap.constraints["max_bytes_billed"], 100000000)

    def test_allowed_false_with_reason(self):
        raw = {
            "gcp.gke.deploy": {
                "source_skill": "google_skills_repo:gke",
                "exposed_as": "gke.deploy",
                "allowed": False,
                "side_effect": "deployment",
                "reason": "Deployment is outside this workflow.",
            }
        }
        result = parse_skill_capabilities(raw, self._sources())
        cap = result["gcp.gke.deploy"]
        self.assertFalse(cap.allowed)
        self.assertEqual(cap.reason, "Deployment is outside this workflow.")

    def test_provenance_required(self):
        raw = {
            "gcp.bigquery.read_dataset": {
                "source_skill": "local_skills:bigquery",
                "exposed_as": "bigquery.read_dataset",
                "allowed": True,
                "side_effect": "none",
                "provenance_required": {"input": "trusted_or_user_confirmed"},
            }
        }
        result = parse_skill_capabilities(raw, self._sources())
        self.assertIsNotNone(result["gcp.bigquery.read_dataset"].provenance_required)

    def test_undeclared_source_raises(self):
        raw = {
            "bad.cap": {
                "source_skill": "missing_source:something",
                "exposed_as": "something",
                "allowed": True,
                "side_effect": "none",
            }
        }
        with self.assertRaises(ValueError, msg="Should fail on unknown source"):
            parse_skill_capabilities(raw, self._sources())

    def test_non_skill_capabilities_ignored(self):
        raw = {
            "read_file": {"allowed": True},
            "skill_cap": {
                "source_skill": "local_skills:email",
                "exposed_as": "email",
                "allowed": True,
                "side_effect": "external_communication",
            },
        }
        result = parse_skill_capabilities(raw, self._sources())
        self.assertNotIn("read_file", result)
        self.assertIn("skill_cap", result)

    def test_exposed_as_defaults_to_name(self):
        raw = {
            "my.cap": {
                "source_skill": "local_skills:cap",
                "allowed": True,
                "side_effect": "none",
            }
        }
        result = parse_skill_capabilities(raw, self._sources())
        self.assertEqual(result["my.cap"].exposed_as, "my.cap")


class TestCompileWorldManifestWithSkills(unittest.TestCase):

    def test_full_manifest_with_skill_sources(self):
        path = _write_manifest("""
            world_id: safe-skills-demo

            skill_sources:
              google_skills_repo:
                type: git
                url: https://github.com/google/skills
                trust_level: external_verified_source
                import_mode: explicit_only

            allowed_tools:
              - read_file

            capabilities:
              read_file:
                allowed: true
              gcp.bigquery.read_dataset:
                source_skill: google_skills_repo:bigquery
                exposed_as: bigquery.read_dataset
                allowed: true
                side_effect: none
              gcp.gke.deploy:
                source_skill: google_skills_repo:gke
                exposed_as: gke.deploy
                allowed: false
                side_effect: deployment
                reason: "Outside this workflow."
        """)
        try:
            config = compile_world_manifest(path)
        finally:
            os.unlink(path)

        self.assertIn("skill_sources", config)
        self.assertIn("google_skills_repo", config["skill_sources"])

        skill_caps = config["skill_capabilities"]
        self.assertIn("gcp.bigquery.read_dataset", skill_caps)
        self.assertIn("gcp.gke.deploy", skill_caps)

        bq = skill_caps["gcp.bigquery.read_dataset"]
        self.assertEqual(bq.exposed_as, "bigquery.read_dataset")
        self.assertTrue(bq.allowed)

        gke = skill_caps["gcp.gke.deploy"]
        self.assertFalse(gke.allowed)
        self.assertEqual(gke.reason, "Outside this workflow.")

    def test_manifest_without_skill_sources_compiles_cleanly(self):
        path = _write_manifest("""
            world_id: classic
            allowed_tools:
              - read_file
            capabilities:
              read_file:
                allowed: true
        """)
        try:
            config = compile_world_manifest(path)
        finally:
            os.unlink(path)
        self.assertEqual(config["skill_sources"], {})
        self.assertEqual(config["skill_capabilities"], {})

    def test_manifest_with_invalid_source_ref_raises(self):
        path = _write_manifest("""
            world_id: bad
            skill_sources:
              real_source:
                type: local
                path: /tmp
            allowed_tools: []
            capabilities:
              bad_cap:
                source_skill: nonexistent_source:skill
                exposed_as: skill
                allowed: true
                side_effect: none
        """)
        try:
            with self.assertRaises(ValueError):
                compile_world_manifest(path)
        finally:
            os.unlink(path)

    def test_undeclared_imported_skill_not_in_skill_capabilities(self):
        """A skill that exists in the source but is not declared in capabilities is absent."""
        path = _write_manifest("""
            world_id: selective
            skill_sources:
              local_src:
                type: local
                path: /tmp
            allowed_tools: []
            capabilities:
              known_cap:
                source_skill: local_src:known
                exposed_as: known
                allowed: true
                side_effect: none
        """)
        try:
            config = compile_world_manifest(path)
        finally:
            os.unlink(path)
        # Only the declared capability is present; undeclared skills are absent
        self.assertEqual(set(config["skill_capabilities"].keys()), {"known_cap"})


if __name__ == "__main__":
    unittest.main()
