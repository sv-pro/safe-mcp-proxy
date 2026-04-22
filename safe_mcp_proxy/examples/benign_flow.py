from pathlib import Path

from safe_mcp_proxy.main import build_executor
from safe_mcp_proxy.provenance import Provenance


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parents[2]
    executor = build_executor(base_dir)
    result = executor.execute("read_file", {"path": "README.md"}, Provenance.from_source("cli"))
    print(result)
