1/ Your AI agent's entire reality is declared in one YAML file. Here's how that works in safe-mcp-proxy.

2/ world_manifest.yaml lists which tools exist, which capabilities are enabled, and what taint rules apply. Compiled once at startup. Never reloaded at runtime.

3/ Why never reloaded? Because it makes every audit log entry deterministic. Every decision maps to an exact policy snapshot. You can replay past decisions and know exactly what policy was active.

4/ Parameterized capabilities let you lock individual args. send_me_email = send_email with "to" locked to your address. Even a successful injection can't change the recipient.

5/ Different agents, different worlds. A research agent runs in a read-only world. An ops agent runs in a scoped write world. Same codebase. Different manifests. Different realities.

6/ The manifest is the policy. Not code, not a database — a YAML file you can read, commit, diff, and audit.

7/ https://github.com/sv-pro/safe-mcp-proxy
