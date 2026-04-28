1/ There are two ways an AI agent tool call can fail in safe-mcp-proxy. One is much stronger than the other.

2/ DENY: a visible tool was blocked by policy. The agent knows the tool exists. A prompt injection attack has a target.

3/ ABSENT: the tool does not exist in this world. The agent was never told about it. The injection has no target.

4/ "Some actions are denied. Others do not exist." — that's the whole philosophy.

5/ The policy engine enforces strict ordering: ABSENT checks run before DENY checks. A tool not in the world manifest cannot trigger a taint violation, a schema check, or an approval gate. It simply doesn't exist.

6/ You cannot be manipulated into calling something you've never seen.

7/ Run it yourself: python -m safe_mcp_proxy.examples.absent_tool_case → ABSENT / tool_not_allowlisted

8/ Full code + docs: https://github.com/sv-pro/safe-mcp-proxy
