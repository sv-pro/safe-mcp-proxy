#!/usr/bin/env python3
"""MCPZero Demo — deterministic prevention of agent exploits via Safe MCP Proxy.

Usage:
    python -m mcpzero.demo                      # run all scenarios
    python -m mcpzero.demo --scenario email_injection
    python -m mcpzero.demo --no-color
    python -m mcpzero.demo --output results/

Both passes (baseline and protected) are run with identical inputs.
Only the execution layer differs.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

from attacks.loader import AttackScenario, load_all, ATTACKS_DIR
from mcpzero.observer.observer import ExecutionObserver
from mcpzero.runner.interface import ScenarioRunner
from mcpzero.verdict.engine import Verdict, compare, save as save_verdicts
from mcpzero.metrics.reporter import print_summary, save as save_metrics

_GREEN  = "\033[92m"
_RED    = "\033[91m"
_YELLOW = "\033[93m"
_BOLD   = "\033[1m"
_RESET  = "\033[0m"

_DECISION_COLOUR = {"ALLOW": _GREEN, "DENY": _RED, "ABSENT": _YELLOW}


def _col(text: str, colour: str, use_color: bool) -> str:
    return f"{colour}{text}{_RESET}" if use_color else text


def _decision_str(decision: str, use_color: bool) -> str:
    return _col(decision, _DECISION_COLOUR.get(decision, ""), use_color)


def _print_scenario_header(scenario: AttackScenario, use_color: bool) -> None:
    bar = "=" * 60
    print(f"\n{bar}")
    title = _col(scenario.name, _BOLD, use_color)
    print(f"  Scenario : {title}  ({scenario.type})")
    print(f"  Channel  : {scenario.source_channel}")
    print(bar)


def _print_run_block(label: str, steps: List[dict], use_color: bool) -> None:
    print(f"\n  [{label.upper()}]")
    for step in steps:
        d = _decision_str(step["decision"], use_color)
        rule = f"  ({step.get('rule', '')})" if step.get("rule") else ""
        print(f"    {step['tool']} → {d}{rule}")


def _print_verdict(verdict: Verdict, use_color: bool) -> None:
    if verdict.demo_pass:
        status = _col("DEMO PASS", _GREEN, use_color)
        detail = "attack succeeded in baseline, proxy blocked it"
    elif not verdict.attack_succeeded:
        status = _col("SKIP", _YELLOW, use_color)
        detail = "attack did not succeed in baseline"
    else:
        status = _col("DEMO FAIL", _RED, use_color)
        detail = "proxy did NOT block the attack"
    print(f"\n  Verdict: {status} — {detail}")


def run_all(
    scenarios: List[AttackScenario],
    output_dir: Path | None,
    use_color: bool,
) -> List[Verdict]:
    observer = ExecutionObserver()
    baseline_runner  = ScenarioRunner(mode="baseline")
    protected_runner = ScenarioRunner(mode="protected")
    verdicts: List[Verdict] = []

    for scenario in scenarios:
        _print_scenario_header(scenario, use_color)

        b = baseline_runner.run(scenario, observer=observer)
        p = protected_runner.run(scenario, observer=observer)
        v = compare(scenario, b, p)
        verdicts.append(v)

        _print_run_block("baseline",  b.steps, use_color)
        _print_run_block("protected", p.steps, use_color)
        _print_verdict(v, use_color)

    print(f"\n{'=' * 60}")
    print("  Summary")
    print(f"{'=' * 60}")
    print_summary(verdicts)
    print(f"\n  Trace log: {observer.log_path}")

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        save_verdicts(verdicts, output_dir / "verdict.json")
        save_metrics(verdicts,  output_dir / "metrics.json")
        print(f"  Results  : {output_dir}")

    return verdicts


def main() -> None:
    parser = argparse.ArgumentParser(
        description="MCPZero Demo — Safe MCP Proxy prevents agent exploits deterministically"
    )
    parser.add_argument("--scenario", default=None,
                        help="Run a single scenario by name (default: all)")
    parser.add_argument("--no-color", action="store_true",
                        help="Disable ANSI colour output")
    parser.add_argument("--output", default=None, metavar="DIR",
                        help="Write verdict.json and metrics.json to this directory")
    args = parser.parse_args()

    use_color = not args.no_color and sys.stdout.isatty()

    scenarios = load_all(ATTACKS_DIR)
    if args.scenario:
        scenarios = [s for s in scenarios if s.name == args.scenario]
        if not scenarios:
            print(f"No scenario named {args.scenario!r}", file=sys.stderr)
            sys.exit(1)

    output_dir = Path(args.output) if args.output else None
    verdicts = run_all(scenarios, output_dir, use_color)

    # Exit non-zero if any demo failed (all should pass for CI)
    if not all(v.demo_pass for v in verdicts):
        sys.exit(1)


if __name__ == "__main__":
    main()
