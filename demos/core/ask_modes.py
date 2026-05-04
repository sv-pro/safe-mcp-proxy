from pathlib import Path

from safe_mcp_proxy.execution_mode import ExecutionMode
from safe_mcp_proxy.main import build_executor
from safe_mcp_proxy.provenance import Provenance


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parents[2]
    executor = build_executor(base_dir)
    payload = {"to": "ops@example.com", "body": "Deploy complete"}

    # INTERACTIVE mode: ASK pauses execution and returns an approval token.
    interactive_prov = Provenance.from_source("cli", execution_mode=ExecutionMode.INTERACTIVE)
    interactive_result = executor.execute("send_email", payload, interactive_prov)
    print("INTERACTIVE:", interactive_result)

    # BACKGROUND mode: no human available — ASK falls back to DENY immediately.
    background_prov = Provenance.from_source("cli", execution_mode=ExecutionMode.BACKGROUND)
    background_result = executor.execute("send_email", payload, background_prov)
    print("BACKGROUND: ", background_result)
