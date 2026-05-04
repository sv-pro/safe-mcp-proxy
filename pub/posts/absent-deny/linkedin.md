There are two ways an AI agent tool call can fail. They look the same from the outside, but one is much stronger than the other.

**DENY** means a visible tool was blocked. The agent knows the tool exists. A sophisticated attacker has a target.

**ABSENT** means the tool does not exist in this world. The agent was never told about it. There is no target to exploit.

This is the core of safe-mcp-proxy: "Some actions are denied. Others do not exist."

If a tool is not in the world manifest, it is absent — not denied. An agent cannot be manipulated into calling something it has never seen.

The policy engine enforces this with strict ordering: ABSENT checks run before DENY checks. A hidden tool cannot trigger a taint violation. It cannot appear in any error message. It simply isn't there.

The difference sounds subtle. The security implications are not.

→ Run the demo: python -m demos.core.absent_tool_case
→ Code and docs: https://github.com/sv-pro/safe-mcp-proxy
