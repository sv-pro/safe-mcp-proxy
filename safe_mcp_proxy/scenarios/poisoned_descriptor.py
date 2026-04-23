from safe_mcp_proxy.scenarios import Scenario, register


def _mutate_schema(executor) -> None:
    tool = executor.registry.get_tool("read_file")
    if tool:
        tool.schema["properties"]["encoding"] = {"type": "string"}


register(Scenario(
    name="poisoned_descriptor",
    description="Schema mutated at runtime — triggers descriptor drift detection",
    tool="read_file",
    payload={"path": "README.md"},
    source_channel="cli",
    expected_decision="DENY",
    expected_rule="descriptor_drift",
    setup=_mutate_schema,
))
