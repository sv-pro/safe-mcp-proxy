"""Skill source registry — import and track external skills without exposing them.

Imported skills are never auto-exposed to the agent. A skill must be explicitly
declared in the world manifest before it can appear in list_tools().
"""
import datetime
import hashlib
import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SkillSource:
    name: str
    source_type: str        # "local" | "git"
    path: Optional[str] = None
    url: Optional[str] = None
    commit: Optional[str] = None
    version: Optional[str] = None
    trust_level: str = "external_unverified"
    import_mode: str = "explicit_only"


@dataclass
class ImportedSkill:
    name: str
    source_name: str
    path: str
    content_hash: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    import_timestamp: str = ""


_SKILL_EXTENSIONS = {".yaml", ".yml", ".json", ".py"}


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class SkillSourceRegistry:
    """Registry of external skill sources and their imported skills.

    Imported skills are catalogued for inspection but never made executable
    by this registry. Exposure requires an explicit world manifest declaration.
    """

    def __init__(self) -> None:
        self._sources: Dict[str, SkillSource] = {}
        self._skills: Dict[str, ImportedSkill] = {}  # key: "source_name:skill_name"

    # ------------------------------------------------------------------
    # Source management
    # ------------------------------------------------------------------

    def register_source(self, source: SkillSource) -> None:
        self._sources[source.name] = source

    def get_source(self, name: str) -> Optional[SkillSource]:
        return self._sources.get(name)

    def list_sources(self) -> List[SkillSource]:
        return list(self._sources.values())

    # ------------------------------------------------------------------
    # Import
    # ------------------------------------------------------------------

    def import_from_source(self, source_name: str) -> List[ImportedSkill]:
        """Import skills from the named source into the registry.

        Only local directory sources are supported for active import.
        Git sources store metadata only (no network access at import time).
        """
        source = self._sources.get(source_name)
        if source is None:
            raise KeyError(f"Source '{source_name}' not registered")

        if source.source_type == "local":
            return self._import_local(source)
        if source.source_type == "git":
            return self._import_git_metadata(source)
        raise ValueError(f"Unsupported source_type '{source.source_type}' for source '{source_name}'")

    def _import_local(self, source: SkillSource) -> List[ImportedSkill]:
        if not source.path:
            raise ValueError(f"Source '{source.name}' has no path configured")
        if not os.path.isdir(source.path):
            raise ValueError(f"Source '{source.name}' path does not exist: {source.path}")

        imported: List[ImportedSkill] = []
        for filename in sorted(os.listdir(source.path)):
            ext = os.path.splitext(filename)[1].lower()
            if ext not in _SKILL_EXTENSIONS:
                continue
            filepath = os.path.join(source.path, filename)
            if not os.path.isfile(filepath):
                continue
            with open(filepath, "rb") as fh:
                raw = fh.read()
            skill_name = os.path.splitext(filename)[0]
            skill = ImportedSkill(
                name=skill_name,
                source_name=source.name,
                path=filepath,
                content_hash=_hash_bytes(raw),
                metadata={},
                import_timestamp=_utc_now(),
            )
            self._skills[f"{source.name}:{skill_name}"] = skill
            imported.append(skill)
        return imported

    def _import_git_metadata(self, source: SkillSource) -> List[ImportedSkill]:
        """Record git source metadata without fetching content."""
        skill_name = source.name
        skill = ImportedSkill(
            name=skill_name,
            source_name=source.name,
            path=source.url or "",
            content_hash="",
            metadata={
                "url": source.url,
                "commit": source.commit,
                "version": source.version,
                "trust_level": source.trust_level,
                "note": "git source — content not fetched at import time",
            },
            import_timestamp=_utc_now(),
        )
        self._skills[f"{source.name}:{skill_name}"] = skill
        return [skill]

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def list_skills(self) -> List[ImportedSkill]:
        return list(self._skills.values())

    def get_skill(self, source_name: str, skill_name: str) -> Optional[ImportedSkill]:
        return self._skills.get(f"{source_name}:{skill_name}")

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def export_manifest(self) -> Dict[str, Any]:
        """Return the import manifest as a serialisable dict."""
        return {
            "sources": {
                name: {
                    "source_type": s.source_type,
                    "path": s.path,
                    "url": s.url,
                    "commit": s.commit,
                    "version": s.version,
                    "trust_level": s.trust_level,
                    "import_mode": s.import_mode,
                }
                for name, s in self._sources.items()
            },
            "skills": {
                key: {
                    "name": skill.name,
                    "source_name": skill.source_name,
                    "path": skill.path,
                    "content_hash": skill.content_hash,
                    "metadata": skill.metadata,
                    "import_timestamp": skill.import_timestamp,
                }
                for key, skill in self._skills.items()
            },
        }

    def save_manifest(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.export_manifest(), fh, indent=2)


def _utc_now() -> str:
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
