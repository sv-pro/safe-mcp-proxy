import json
import os
import tempfile
import unittest

from safe_mcp_proxy.skill_registry import ImportedSkill, SkillSource, SkillSourceRegistry


class TestSkillSourceRegistry(unittest.TestCase):

    def _make_local_source(self, tmpdir: str, name: str = "local_skills") -> SkillSource:
        return SkillSource(name=name, source_type="local", path=tmpdir)

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def test_register_and_retrieve_source(self):
        reg = SkillSourceRegistry()
        src = SkillSource(name="test_src", source_type="local", path="/tmp")
        reg.register_source(src)
        self.assertIs(reg.get_source("test_src"), src)

    def test_list_sources(self):
        reg = SkillSourceRegistry()
        reg.register_source(SkillSource(name="a", source_type="local", path="/tmp"))
        reg.register_source(SkillSource(name="b", source_type="git", url="https://example.com"))
        self.assertEqual({s.name for s in reg.list_sources()}, {"a", "b"})

    # ------------------------------------------------------------------
    # Local import
    # ------------------------------------------------------------------

    def test_import_local_yaml(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_file = os.path.join(tmpdir, "email.yaml")
            with open(skill_file, "wb") as f:
                f.write(b"name: email\nactions:\n  - send\n")
            reg = SkillSourceRegistry()
            reg.register_source(self._make_local_source(tmpdir))
            skills = reg.import_from_source("local_skills")
            self.assertEqual(len(skills), 1)
            self.assertEqual(skills[0].name, "email")
            self.assertEqual(skills[0].source_name, "local_skills")

    def test_import_local_content_hash(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            content = b"name: bigquery\n"
            with open(os.path.join(tmpdir, "bigquery.yaml"), "wb") as f:
                f.write(content)
            reg = SkillSourceRegistry()
            reg.register_source(self._make_local_source(tmpdir))
            skills = reg.import_from_source("local_skills")
            import hashlib
            expected = hashlib.sha256(content).hexdigest()
            self.assertEqual(skills[0].content_hash, expected)

    def test_import_local_multiple_extensions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            for fname in ["a.yaml", "b.yml", "c.json", "d.py", "e.txt"]:
                with open(os.path.join(tmpdir, fname), "wb") as f:
                    f.write(b"x")
            reg = SkillSourceRegistry()
            reg.register_source(self._make_local_source(tmpdir))
            skills = reg.import_from_source("local_skills")
            names = {s.name for s in skills}
            self.assertEqual(names, {"a", "b", "c", "d"})  # .txt excluded

    def test_import_local_nonexistent_path_raises(self):
        reg = SkillSourceRegistry()
        reg.register_source(SkillSource(name="bad", source_type="local", path="/nonexistent_xyz"))
        with self.assertRaises(ValueError):
            reg.import_from_source("bad")

    def test_import_unregistered_source_raises(self):
        reg = SkillSourceRegistry()
        with self.assertRaises(KeyError):
            reg.import_from_source("missing")

    # ------------------------------------------------------------------
    # Git metadata import
    # ------------------------------------------------------------------

    def test_import_git_metadata_no_network(self):
        reg = SkillSourceRegistry()
        reg.register_source(SkillSource(
            name="google_skills",
            source_type="git",
            url="https://github.com/google/skills",
            commit="abc123",
            version="1.0.0",
            trust_level="external_verified_source",
        ))
        skills = reg.import_from_source("google_skills")
        self.assertEqual(len(skills), 1)
        self.assertIn("url", skills[0].metadata)
        self.assertEqual(skills[0].metadata["url"], "https://github.com/google/skills")
        self.assertEqual(skills[0].content_hash, "")  # no content fetched

    # ------------------------------------------------------------------
    # No auto-exposure
    # ------------------------------------------------------------------

    def test_imported_skills_not_in_tool_registry(self):
        """Imported skills must never appear in ToolRegistry automatically."""
        from safe_mcp_proxy.registry import ToolRegistry
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "email.yaml"), "wb") as f:
                f.write(b"name: email\n")
            skill_reg = SkillSourceRegistry()
            skill_reg.register_source(self._make_local_source(tmpdir))
            skill_reg.import_from_source("local_skills")

            # ToolRegistry with empty allowlist — skill must not appear
            tool_reg = ToolRegistry.with_mock_tools(allowlist=[])
            self.assertIsNone(tool_reg.get_tool("email"))
            self.assertEqual(len(skill_reg.list_skills()), 1)

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def test_get_skill_by_source_and_name(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "bq.yaml"), "wb") as f:
                f.write(b"x")
            reg = SkillSourceRegistry()
            reg.register_source(self._make_local_source(tmpdir))
            reg.import_from_source("local_skills")
            skill = reg.get_skill("local_skills", "bq")
            self.assertIsNotNone(skill)
            self.assertEqual(skill.name, "bq")

    def test_get_skill_missing_returns_none(self):
        reg = SkillSourceRegistry()
        self.assertIsNone(reg.get_skill("no_source", "no_skill"))

    # ------------------------------------------------------------------
    # Manifest export / persistence
    # ------------------------------------------------------------------

    def test_export_manifest_structure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "skill.yaml"), "wb") as f:
                f.write(b"x")
            reg = SkillSourceRegistry()
            reg.register_source(self._make_local_source(tmpdir))
            reg.import_from_source("local_skills")
            manifest = reg.export_manifest()
            self.assertIn("sources", manifest)
            self.assertIn("skills", manifest)
            self.assertIn("local_skills", manifest["sources"])
            self.assertEqual(len(manifest["skills"]), 1)

    def test_save_manifest_writes_valid_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "s.yaml"), "wb") as f:
                f.write(b"x")
            reg = SkillSourceRegistry()
            reg.register_source(self._make_local_source(tmpdir))
            reg.import_from_source("local_skills")

            out = os.path.join(tmpdir, "import_manifest.json")
            reg.save_manifest(out)
            with open(out, "r") as f:
                data = json.load(f)
            self.assertIn("sources", data)
            self.assertIn("skills", data)


if __name__ == "__main__":
    unittest.main()
