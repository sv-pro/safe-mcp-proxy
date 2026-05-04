# `skill_registry.py`

## Role

Skill source registry — imports and tracks external skills without exposing them to the agent.

## Key symbols

| Name | Kind | Description |
|------|------|-------------|
| `SkillSource` | dataclass | A registered external source: name, source_type ("local"\|"git"), path, url, commit, version, trust_level, import_mode |
| `ImportedSkill` | dataclass | A catalogued skill: name, source_name, path, content_hash (SHA256), metadata, import_timestamp |
| `SkillSourceRegistry` | class | Manages sources and imported skills; enforces the no-auto-exposure invariant |
| `SkillSourceRegistry.register_source()` | method | Add a `SkillSource` to the registry |
| `SkillSourceRegistry.import_from_source()` | method | Import skills from a named source; dispatches to local or git adapter |
| `SkillSourceRegistry.list_skills()` | method | Return all catalogued `ImportedSkill` records |
| `SkillSourceRegistry.get_skill()` | method | Look up a skill by `(source_name, skill_name)` |
| `SkillSourceRegistry.export_manifest()` | method | Return a serialisable dict of all sources and skills |
| `SkillSourceRegistry.save_manifest()` | method | Write the import manifest to a JSON file |

## Core invariant

> Imported skills are never auto-exposed to the agent.

A skill catalogued by `SkillSourceRegistry` does not appear in `list_tools()` unless it is also explicitly declared in the world manifest. The registry and the `ToolRegistry` are completely separate; there is no automatic bridge between them.

## Source types

| source_type | Behaviour |
|-------------|-----------|
| `"local"` | Reads files from a local directory. Supported extensions: `.yaml`, `.yml`, `.json`, `.py`. Computes SHA256 hash from raw file bytes. |
| `"git"` | Stores metadata (url, commit, version) without network access. `content_hash` is empty string — no content is fetched. |

## Content hash

SHA256 of the raw file bytes (not the parsed structure). Allows detecting file-level changes independently of schema drift tracked by [[src/safe_mcp_proxy/descriptor]].

## Key: `"source_name:skill_name"`

Skills are stored internally under a compound key `"{source_name}:{skill_name}"` to allow the same skill name from different sources to coexist without collision.

## Depends on

- `hashlib`, `json`, `os`, `datetime` (stdlib only)

## Used by

- EPIC 10 demo: `demos/safe_skills/`
- World manifest compiler extension (planned — [[src/safe_mcp_proxy/compiler]])

## See also

- [[world-manifest]] — skills become executable only after explicit manifest declaration
- [[src/safe_mcp_proxy/descriptor]] — SHA256 schema drift detection (parallel mechanism)
- [[absent-deny]] — the ABSENT semantic that prevents undeclared skills from reaching the agent
