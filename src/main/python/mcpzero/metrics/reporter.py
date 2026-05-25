"""Metrics & reporting — computes ASR and block rate across verdict sets."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from mcpzero.verdict.engine import Verdict


def compute_asr(verdicts: List[Verdict]) -> float:
    """Attack Success Rate: fraction of scenarios where the attack succeeds in baseline."""
    if not verdicts:
        return 0.0
    return sum(1 for v in verdicts if v.attack_succeeded) / len(verdicts)


def compute_block_rate(verdicts: List[Verdict]) -> float:
    """Block rate: fraction of baseline-successful attacks that the proxy blocked."""
    attackable = [v for v in verdicts if v.attack_succeeded]
    if not attackable:
        return 0.0
    return sum(1 for v in attackable if v.proxy_blocked) / len(attackable)


def to_dict(verdicts: List[Verdict]) -> Dict[str, Any]:
    return {
        "total":      len(verdicts),
        "asr":        compute_asr(verdicts),
        "block_rate": compute_block_rate(verdicts),
        "demo_pass":  sum(1 for v in verdicts if v.demo_pass),
    }


def save(verdicts: List[Verdict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as fh:
        json.dump(to_dict(verdicts), fh, indent=2)


def print_summary(verdicts: List[Verdict]) -> None:
    asr = compute_asr(verdicts)
    br  = compute_block_rate(verdicts)
    passes = sum(1 for v in verdicts if v.demo_pass)
    print(f"  Scenarios run : {len(verdicts)}")
    print(f"  ASR (baseline): {asr:.0%}")
    print(f"  Block rate    : {br:.0%}")
    print(f"  Demo pass     : {passes}/{len(verdicts)}")
