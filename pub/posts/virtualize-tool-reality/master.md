# The MCP Supply Chain Problem: Why Filters Fail

As AI agents increasingly connect to Model Context Protocol (MCP) servers to discover and invoke tools, a new attack surface emerges: the runtime supply chain. 

When an agent connects to an MCP server, it trusts whatever tools the server advertises. This opens the door to several critical risks:
- **Deceptive Schemas**: Malicious MCP servers can inject tools that look benign but do something else entirely.
- **Descriptor Drift**: A tool's schema can silently mutate between startup and invocation. The agent thinks it's calling `read_file`, but the underlying logic has changed.
- **Prompt Injection**: If an agent reads a poisoned web page or email, it can be manipulated into calling *any* tool currently sitting in its registry.

**Why standard filters don't save us:**
Standard input filters and LLM alignment can only do so much. If a dangerous tool exists and the agent can see it, the agent can be tricked into calling it. The attack surface isn't just the prompt; it's the tool list itself.

### The Solution: Virtualize Tool Reality

To solve this, we built **safe-mcp-proxy**. It introduces a single, powerful concept:
> *"Some actions are denied. Others do not exist."*

Instead of just trying to block bad actions (DENY), safe-mcp-proxy acts as a narrow control plane that completely virtualizes the agent's reality.
- If a tool is not in the static `world_manifest.yaml` allowlist, it is **ABSENT**. It is completely hidden from the agent. An agent cannot be manipulated into calling a tool it doesn't know exists.
- If a tool *is* visible, but the request comes from a tainted source channel (like an email) or its schema has drifted, it is **DENIED** by deterministic policy.

By ensuring nothing reaches the agent without passing through this proxy, we move from reactive filtering to structural isolation.

Check out the repository and try the interactive demos: 
🔗 [https://github.com/sv-pro/safe-mcp-proxy](https://github.com/sv-pro/safe-mcp-proxy)
