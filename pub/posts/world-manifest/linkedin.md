In safe-mcp-proxy, your agent's entire reality is declared in a single YAML file: world_manifest.yaml.

It lists which tools exist, which capabilities are enabled, and what happens to tainted requests. That's it. Everything else is derived from this file.

The manifest is compiled once at startup and never reloaded at runtime. This is deliberate: because the policy never changes while the process runs, every decision in the audit log maps to an exact policy snapshot. You can replay a decision made three months ago and know exactly what policy was active.

It also supports parameterized capabilities — constrained projections of base tools. An example: send_me_email is a form of send_email where the recipient is locked to "owner@example.com" in the manifest. Even a successful prompt injection cannot redirect the email. The "to" field doesn't exist from the actor's perspective.

Different agents can operate in different worlds from the same codebase. A research agent runs in a read-only world. An operations agent runs in a world with scoped write access. The agent code doesn't change — the world declaration does.

→ Code and docs: https://github.com/sv-pro/safe-mcp-proxy
