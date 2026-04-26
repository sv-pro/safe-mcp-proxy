from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

ATTACKS_DIR = Path(__file__).parent

VALID_TYPES = {"email_injection", "tool_chain", "mcp_poison"}
VALID_CHANNELS = {"cli", "email", "web", "tool_output"}
VALID_DECISIONS = {"ALLOW", "DENY", "ABSENT"}


@dataclass
class AttackStep:
    tool: str
    payload: Dict[str, Any]


@dataclass
class AttackScenario:
    name: str
    description: str
    type: str
    source_channel: str
    steps: List[AttackStep]
    expected_baseline: str
    expected_protected: str
    document: str = ""
    poison_tool: Optional[Dict[str, Any]] = field(default=None)


def _parse(data: Dict[str, Any], path: Path) -> AttackScenario:
    required = ("name", "description", "type", "source_channel", "steps", "expected")
    for f in required:
        if f not in data:
            raise ValueError(f"{path}: missing required field '{f}'")

    if data["type"] not in VALID_TYPES:
        raise ValueError(f"{path}: unknown type '{data['type']}'; must be one of {VALID_TYPES}")

    if data["source_channel"] not in VALID_CHANNELS:
        raise ValueError(f"{path}: unknown source_channel '{data['source_channel']}'")

    expected = data["expected"]
    for key in ("baseline", "protected"):
        if key not in expected:
            raise ValueError(f"{path}: expected.{key} is required")
        if expected[key] not in VALID_DECISIONS:
            raise ValueError(f"{path}: expected.{key} must be one of {VALID_DECISIONS}")

    steps = [
        AttackStep(tool=s["tool"], payload=s.get("payload", {}))
        for s in data["steps"]
    ]

    document = ""
    if "document" in data:
        document = load_document(path.parent / data["document"])

    return AttackScenario(
        name=data["name"],
        description=data["description"].strip(),
        type=data["type"],
        source_channel=data["source_channel"],
        steps=steps,
        expected_baseline=expected["baseline"],
        expected_protected=expected["protected"],
        document=document,
        poison_tool=data.get("poison_tool"),
    )


def load_document(path: Path) -> str:
    """Read a raw document file (e.g. .md) and return its text content."""
    with open(path) as fh:
        return fh.read()


def load(path: Path) -> AttackScenario:
    """Load and validate a single YAML or JSON attack scenario file."""
    with open(path) as fh:
        data = json.load(fh) if path.suffix == ".json" else yaml.safe_load(fh)
    return _parse(data, path)


def load_all(directory: Path = ATTACKS_DIR) -> List[AttackScenario]:
    """Load all .yaml and .json scenario files from a directory (skips schema.yaml)."""
    scenarios = []
    for p in sorted(directory.glob("*.yaml")) + sorted(directory.glob("*.json")):
        if p.name == "schema.yaml":
            continue
        scenarios.append(load(p))
    return scenarios
