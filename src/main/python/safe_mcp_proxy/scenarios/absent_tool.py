from safe_mcp_proxy.scenarios import Scenario, register

register(Scenario(
    name="absent_tool",
    description="Tool not in world allowlist — does not exist in this world",
    tool="dangerous_exec",
    payload={"cmd": "rm -rf /"},
    source_channel="cli",
    expected_decision="ABSENT",
    expected_rule="tool_not_allowlisted",
))
