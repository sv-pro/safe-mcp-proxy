from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

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


def _parse(data: Dict[str, Any], path: Path) -> AttackScenario:
    required = ("name", "description", "type", "source_channel", "steps", "expected")
    for field in required:
        if field not in data:
            raise ValueError(f"{path}: missing required field '{field}'")

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

    return AttackScenario(
        name=data["name"],
        description=data["description"].strip(),
        type=data["type"],
        source_channel=data["source_channel"],
        steps=steps,
        expected_baseline=expected["baseline"],
        expected_protected=expected["protected"],
    )


def load(path: Path) -> AttackScenario:
    """Load and validate a single YAML attack scenario file."""
    with open(path) as fh:
        data = yaml.safe_load(fh)
    return _parse(data, path)


def load_all(directory: Path = ATTACKS_DIR) -> List[AttackScenario]:
    """Load all .yaml scenario files from a directory (skips schema.yaml)."""
    scenarios = []
    for p in sorted(directory.glob("*.yaml")):
        if p.name == "schema.yaml":
            continue
        scenarios.append(load(p))
    return scenarios
