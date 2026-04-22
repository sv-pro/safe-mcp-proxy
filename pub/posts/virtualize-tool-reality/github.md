# 🚀 Introducing safe-mcp-proxy: Virtualize Tool Reality

We're excited to share **safe-mcp-proxy**, a minimal, deterministic control plane for MCP that mitigates runtime supply-chain risks.

### The Problem
MCP allows agents to discover tools at runtime, but this creates a massive vulnerability. Agents trust whatever the server advertises. Standard filters fail because if a dangerous tool exists and is visible, prompt injection can trigger it. 

### The Solution
We need to shift from reactive filtering to **structural isolation**. safe-mcp-proxy sits between the agent and the registry. 

Our core philosophy is simple: **"Some actions are denied. Others do not exist."**
- **ABSENT:** If a tool isn't in the static allowlist, the agent never sees it. It cannot call what doesn't exist.
- **DENY:** If a tool is visible but violates our deterministic policy (e.g., tainted source channels, descriptor drift), it is blocked.

### Try it out!
Clone the repo and run our example scenarios to see ALLOW, DENY, and ABSENT in action, complete with an append-only audit log that guarantees deterministic replay.

🔗 [Explore safe-mcp-proxy](https://github.com/sv-pro/safe-mcp-proxy)
