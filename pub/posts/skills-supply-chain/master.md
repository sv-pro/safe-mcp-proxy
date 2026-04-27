# Skills Repositories Are the npm of Agent Capabilities

Google, LangChain, and similar platforms now publish official skills repositories —
curated collections of agent capabilities that can be loaded at runtime. An agent can
discover and activate skills from these external sources dynamically, without the operator
explicitly adding each one to a manifest.

This is a useful capability distribution mechanism. It is also a new attack surface that
most teams haven't yet named.

---

## Static vs dynamic capability surfaces

A static MCP tool registry has a bounded surface. The operator declares tools at startup.
The agent sees exactly those tools. The attack surface is auditable.

```
Static MCP (known surface):
  Manifest declares 3 tools
  Agent sees exactly 3 tools
  Operator can audit all 3
  Attack surface: bounded
```

External skills repositories change this:

```
Dynamic skills (open-ended space):
  Manifest + skills repo = ?
  Agent can discover N skills
  Operator audits manifest only
  Attack surface: unbounded
```

The skills repo is a dependency. Dependencies can be compromised.

---

## The attack chain

Dynamic skills create a dangerous interaction with indirect prompt injection:

```
untrusted content (document, email, web page)
  │
  ▼
hidden instruction ("find a skill that can send email")
  │
  ▼
agent reasoning (follows the instruction)
  │
  ▼
skill discovery / skill loading (scans the skills repo)
  │
  ▼
tool or workflow execution (email.send called with attacker payload)
  │
  ▼
external side effect (data leaves the system)
```

The failure is not that the agent was jailbroken. The failure is that `email.send` was
discoverable. The agent was doing exactly what the injected instruction told it to do,
and it had the capability to do it.

---

## The npm parallel

Software supply-chain attacks (npm, PyPI, Maven) follow a similar pattern: a dependency
that a developer trusts is compromised, and the compromise propagates to every consumer
automatically.

For agent capabilities, the risk is analogous:
- The skills repository is the package registry
- The skill is the package
- The agent is the runtime that loads it
- The skills repo operator is the package author — trusted until compromised

The difference: a compromised npm package affects build-time behavior. A compromised
skill affects *agent actions at runtime* — what the agent can do, right now, in your
production environment.

---

## What doesn't help

**LLM alignment:** Training the model to refuse "find a skill that can send email" is
probabilistic. The right injection phrasing bypasses it. Alignment doesn't prevent the
skill from being discoverable; it only hopes the model won't use it.

**Monitoring:** Detecting the attack after the fact doesn't prevent the exfiltration.
Data has already left the system when you see the alert.

**Allowlisting the skills repo:** If you trust the entire repository, a compromise of
any skill in it expands your attack surface automatically.

---

## The governance gap

The missing piece is not a smarter model or better monitoring. It is a layer that answers:
*"what capabilities are you allowed to use, right now, in this context?"*

Not: "what capabilities exist in the repository?"

The answer to the second question can change anytime — a new skill is added, an existing
one is compromised. The answer to the first question should be under operator control,
declared explicitly, and enforced deterministically.

That is what capability projection addresses. The next post in this series shows how.

---

## See also

- [Repository](https://github.com/sv-pro/safe-mcp-proxy)
- `docs/safe_skills_projection.md` — the full positioning document this post summarizes
- The next post: capability-projection — enforcing a closed world against dynamic skills
