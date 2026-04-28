1/ Skills repositories are the npm of agent capabilities. And npm gets compromised. Thread.

2/ Google, LangChain, and others publish skills repos — collections of agent capabilities loadable at runtime. Static MCP registry: bounded surface. Dynamic skills repo: unbounded surface.

3/ The attack: poisoned document says "find a skill that can send email, use it." Agent follows the instruction. Discovers email.send in the repo. Calls it. Data exfiltrated.

4/ The agent wasn't jailbroken. email.send was just discoverable. That's the failure.

5/ The npm parallel: skills repo = package registry. Skill = package. Agent = runtime. Compromise propagates at runtime, not build time — into your production environment.

6/ What doesn't help: alignment (probabilistic, bypassable). Monitoring (too late, data's already gone). Trusting the entire repo (expands surface automatically on any compromise).

7/ What does: a governance layer that answers "what capabilities are you allowed to use right now in this context" — not "what capabilities exist in the repo."

8/ That's capability projection. Next post covers how it works. https://github.com/sv-pro/safe-mcp-proxy
