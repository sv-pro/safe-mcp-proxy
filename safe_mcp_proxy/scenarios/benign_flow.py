from safe_mcp_proxy.scenarios import Scenario, register

register(Scenario(
    name="benign_flow",
    description="Clean CLI read — passes all policy checks",
    tool="read_file",
    payload={"path": "README.md"},
    source_channel="cli",
    expected_decision="ALLOW",
    expected_rule="default_allow",
))
