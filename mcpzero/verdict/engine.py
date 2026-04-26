"""Verdict engine — compares baseline and protected run results step-by-step."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from attacks.loader import AttackScenario
from mcpzero.runner.interface import RunResult

_BLOCKED = {"DENY", "ABSENT"}


@dataclass
class StepVerdict:
    tool: str
    baseline_decision: str
    protected_decision: str

    @property
    def succeeded_baseline(self) -> bool:
        return self.baseline_decision == "ALLOW"

    @property
    def blocked_protected(self) -> bool:
        return self.protected_decision in _BLOCKED


@dataclass
class Verdict:
    scenario: str
    steps: List[StepVerdict] = field(default_factory=list)

    @property
    def attack_succeeded(self) -> bool:
        """True if at least one step succeeded (ALLOW) in baseline."""
        return any(s.succeeded_baseline for s in self.steps)

    @property
    def proxy_blocked(self) -> bool:
        """True if the proxy blocked at least one step that would have succeeded in baseline.

        Safe steps (e.g. read_file) are expected to stay allowed in protected mode.
        The proxy "won" if it blocked the dangerous step(s) from completing.
        """
        return any(s.succeeded_baseline and s.blocked_protected for s in self.steps)

    @property
    def demo_pass(self) -> bool:
        """Demo is a pass when the attack succeeds baseline but proxy blocks it."""
        return self.attack_succeeded and self.proxy_blocked

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario":                self.scenario,
            "attack_succeeded_baseline": self.attack_succeeded,
            "proxy_blocked":           self.proxy_blocked,
            "demo_pass":               self.demo_pass,
            "steps": [
                {
                    "tool":      s.tool,
                    "baseline":  s.baseline_decision,
                    "protected": s.protected_decision,
                    "blocked":   s.blocked_protected,
                }
                for s in self.steps
            ],
        }


def compare(
    scenario: AttackScenario,
    baseline: RunResult,
    protected: RunResult,
) -> Verdict:
    """Build a Verdict by aligning baseline and protected step results."""
    step_verdicts = []
    for b, p in zip(baseline.steps, protected.steps):
        step_verdicts.append(StepVerdict(
            tool=b["tool"],
            baseline_decision=b["decision"],
            protected_decision=p["decision"],
        ))
    return Verdict(scenario=scenario.name, steps=step_verdicts)


def save(verdicts: List[Verdict], path: Path) -> None:
    """Write verdicts to a JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as fh:
        json.dump([v.to_dict() for v in verdicts], fh, indent=2)
