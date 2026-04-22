import json
from pathlib import Path

from safe_mcp_proxy.main import build_executor
from safe_mcp_proxy.provenance import Provenance

def print_scenario(num: int, title: str, description: str, result: dict):
    print(f"\n{'='*60}")
    print(f"Scenario {num}: {title}")
    print(f"{'-'*60}")
    print(f"Description: {description}")
    print("-" * 60)
    decision = result.get('decision')
    rule = result.get('rule')
    
    if decision == "ALLOW":
        color_start = "\033[92m" # Green
    elif decision == "DENY":
        color_start = "\033[91m" # Red
    elif decision == "ABSENT":
        color_start = "\033[93m" # Yellow
    else:
        color_start = ""
    color_end = "\033[0m"

    print(f"Result: {color_start}{decision}{color_end} (Rule: {rule})")
    print(f"Output: {json.dumps(result.get('result', {}), indent=2)}")

if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent
    print("Initializing safe-mcp-proxy executor...")
    executor = build_executor(base_dir)

    # 1. Normal flow -> ALLOW
    res_allow = executor.execute(
        "read_file", 
        {"path": "README.md"}, 
        Provenance.from_source("cli")
    )
    print_scenario(1, "Normal Flow (ALLOW)", 
                   "A benign CLI request to read a file. The tool is in the allowlist and the source is clean.", 
                   res_allow)

    # 2. Prompt injection attempt -> DENY
    res_injection = executor.execute(
        "send_email",
        {"to": "attacker@example.com", "body": "please exfiltrate"},
        Provenance.from_source("web")
    )
    print_scenario(2, "Prompt Injection Attempt (DENY)", 
                   "An external side-effect tool triggered by a tainted source (web). The policy blocks it deterministically.", 
                   res_injection)

    # 3. Poisoned descriptor -> DENY
    # Mutate the schema to simulate descriptor drift
    tool = executor.registry.get_tool("read_file")
    if tool:
        tool.schema["properties"]["encoding"] = {"type": "string"}
    
    res_poisoned = executor.execute(
        "read_file", 
        {"path": "README.md", "encoding": "utf-8"}, 
        Provenance.from_source("cli")
    )
    print_scenario(3, "Poisoned Tool Descriptor (DENY)", 
                   "The tool's schema was mutated at runtime. The SHA256 drift is detected and the call is blocked before execution.", 
                   res_poisoned)

    # 4. Absent tool -> ABSENT
    res_absent = executor.execute(
        "dangerous_exec", 
        {"cmd": "rm -rf /"}, 
        Provenance.from_source("cli")
    )
    print_scenario(4, "Absent Tool (ABSENT)", 
                   "The tool is not in the world_manifest.yaml allowlist. It is completely hidden. The agent cannot call what does not exist.", 
                   res_absent)

    print(f"\n{'='*60}")
    print("Demo completed. Check safe_mcp_proxy/logs/audit.jsonl for the deterministic audit log.")
