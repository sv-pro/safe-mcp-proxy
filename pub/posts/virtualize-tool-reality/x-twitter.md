Standard AI filters don't work for MCP. If an agent can see a tool, prompt injection can trick the agent into calling it.

The attack surface isn't the prompt. It's the tool list. 

We need to Virtualize Tool Reality. 🧵👇
1/5

Enter safe-mcp-proxy: a deterministic control plane that sits between your agent and the tool registry. 

It solves the MCP supply chain problem where malicious servers inject deceptive schemas or schemas mutate at runtime.
2/5

Our core philosophy: "Some actions are denied. Others do not exist."

There's a big difference between blocking a bad action (DENY) and completely hiding the capability from the agent (ABSENT).
3/5

If a tool isn't in your static world_manifest.yaml, it is ABSENT. An agent cannot be manipulated into calling a tool it doesn't even know exists. 

If it is visible but triggered by a tainted source (like reading an email), it is deterministically DENIED.
4/5

By combining provenance tracking, descriptor drift detection, and an append-only audit log, safe-mcp-proxy replaces reactive filtering with structural isolation.

Try the 4 demo scenarios yourself:
🔗 https://github.com/sv-pro/safe-mcp-proxy
5/5
