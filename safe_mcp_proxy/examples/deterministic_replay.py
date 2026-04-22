import json
import tempfile
from pathlib import Path

from safe_mcp_proxy.executor import Executor
from safe_mcp_proxy.policy_engine import PolicyEngine
from safe_mcp_proxy.provenance import Provenance
from safe_mcp_proxy.registry import ToolRegistry


if __name__ == "__main__":
    audit_file = Path(tempfile.gettempdir()) / "replay_demo_audit.jsonl"
    if audit_file.exists():
        audit_file.unlink()

    registry = ToolRegistry.with_mock_tools(["read_file", "list_repo", "send_email"])
    policy = PolicyEngine(
        allowlist=["read_file", "list_repo", "send_email"],
        capability_map={"read_file": True, "list_repo": True, "send_email": True},
    )
    executor = Executor(registry, policy, str(audit_file), simulate_external=True)

    scenarios = [
        ("read_file",     {"path": "README.md"}, Provenance.from_source("cli")),
        ("send_email",    {"to": "x@y.com"},     Provenance.from_source("web")),
        ("dangerous_exec", {"cmd": "whoami"},    Provenance.from_source("cli")),
        ("list_repo",     {},                    Provenance.from_source("cli")),
    ]

    print("Running 100 tool invocations...")
    for i in range(100):
        tool_name, payload, prov = scenarios[i % len(scenarios)]
        executor.execute(tool_name, payload, prov)

    entries = [json.loads(line) for line in audit_file.read_text().splitlines() if line.strip()]

    print(f"\n{'Tool':<20} {'Recorded':<10} {'Replayed':<10} {'Match'}")
    print("-" * 55)

    matched = 0
    for entry in entries:
        result = executor.replay(entry)
        mark = "OK" if result["matches"] else "FAIL"
        print(f"{entry['tool']:<20} {result['recorded_decision']:<10} {result['replayed_decision']:<10} {mark}")
        if result["matches"]:
            matched += 1

    pct = 100 * matched // len(entries)
    print(f"\nResult: {matched}/{len(entries)} entries matched ({pct}%)")
