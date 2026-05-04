from pathlib import Path

from safe_mcp_proxy.main import build_executor
from safe_mcp_proxy.provenance import Provenance


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parents[2]
    executor = build_executor(base_dir)

    tool = executor.registry.get_tool("read_file")
    if tool:
        tool.schema["properties"]["encoding"] = {"type": "string"}

    result = executor.execute("read_file", {"path": "README.md"}, Provenance.from_source("cli"))
    print(result)
