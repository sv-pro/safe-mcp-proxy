from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


@dataclass
class Scenario:
    name: str
    description: str
    tool: str
    payload: Dict[str, Any]
    source_channel: str
    expected_decision: str
    expected_rule: str
    setup: Optional[Callable] = field(default=None, repr=False)


SCENARIOS: Dict[str, Scenario] = {}


def register(scenario: Scenario) -> None:
    SCENARIOS[scenario.name] = scenario


def get(name: str) -> Scenario:
    try:
        return SCENARIOS[name]
    except KeyError:
        raise KeyError(f"Unknown scenario: {name!r}. Available: {list(SCENARIOS)}")


def names() -> List[str]:
    return list(SCENARIOS)


def run(name: str, executor=None, base_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Execute a named scenario and return the result with pass/fail against expected outcome."""
    scenario = get(name)
    if executor is None:
        from safe_mcp_proxy.main import build_executor
        if base_dir is None:
            base_dir = Path(__file__).resolve().parents[2]
        executor = build_executor(base_dir)
    if scenario.setup is not None:
        scenario.setup(executor)
    from safe_mcp_proxy.provenance import Provenance
    provenance = Provenance.from_source(scenario.source_channel)
    result = executor.execute(scenario.tool, scenario.payload, provenance)
    return {
        "scenario": name,
        "result": result,
        "expected_decision": scenario.expected_decision,
        "expected_rule": scenario.expected_rule,
        "matches": (
            result["decision"] == scenario.expected_decision
            and result["rule"] == scenario.expected_rule
        ),
    }


# Bootstrap: import submodules so they self-register
from safe_mcp_proxy.scenarios import (  # noqa: E402, F401
    absent_tool,
    benign_flow,
    poisoned_descriptor,
    prompt_injection,
)
