"""Scenario execution interface — loads attack scenarios and runs them in either mode.

Mode switch (I7):
  "baseline"  — tools called directly via BaselineAgent (no policy, attack succeeds)
  "protected" — tools routed through SafeMCPProxy (policy enforced, attack blocked)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from attacks.loader import AttackScenario, load, load_all, ATTACKS_DIR

MODES = ("baseline", "protected")


@dataclass
class RunResult:
    mode: str
    scenario_name: str
    steps: List[Dict[str, Any]] = field(default_factory=list)

    def last_decision(self) -> str:
        """Decision of the final step — used for verdict comparison."""
        return self.steps[-1]["decision"] if self.steps else "ABSENT"

    def decisions(self) -> List[str]:
        return [s["decision"] for s in self.steps]


class ScenarioRunner:
    """Executes a single scenario in baseline or protected mode.

    All tool calls are wrapped by an optional ExecutionObserver so that
    every decision is captured in a trace file.
    """

    def __init__(self, mode: str = "baseline") -> None:
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}, got {mode!r}")
        self.mode = mode

    def run(
        self,
        scenario: AttackScenario,
        observer=None,
    ) -> RunResult:
        if self.mode == "baseline":
            from mcpzero.agent.runner import BaselineAgent
            steps = BaselineAgent().run(scenario)
        else:
            from mcpzero.proxy.proxy import SafeMCPProxy
            steps = SafeMCPProxy().run(scenario)

        if observer is not None:
            for step in steps:
                observer.record(
                    mode=self.mode,
                    scenario=scenario.name,
                    tool=step["tool"],
                    payload=step["payload"],
                    decision=step["decision"],
                    rule=step.get("rule"),
                    result=step.get("result"),
                )

        return RunResult(mode=self.mode, scenario_name=scenario.name, steps=steps)


def load_scenario(name_or_path: str) -> AttackScenario:
    """Load a scenario by name (from attacks/) or by explicit file path."""
    p = Path(name_or_path)
    if p.exists():
        return load(p)
    candidates = list(ATTACKS_DIR.glob(f"{name_or_path}.yaml")) + \
                 list(ATTACKS_DIR.glob(f"{name_or_path}.json"))
    if not candidates:
        raise FileNotFoundError(f"No scenario found for {name_or_path!r}")
    return load(candidates[0])


def load_all_scenarios(directory: Path = ATTACKS_DIR) -> List[AttackScenario]:
    """Load every scenario in the attacks corpus."""
    return load_all(directory)
