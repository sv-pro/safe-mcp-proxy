# ZombieAgent Taint-Tracking Demo

Three-act support-agent narrative:

1. A clean support ticket follows the normal path.
2. A poisoned ticket steers the agent into customer-data exfiltration; tainted
   external side effects are denied.
3. The world switches to lockdown, and dangerous tools become absent.

Run:

```bash
bash demos/narratives/zombieagent/run.sh
```

Step-through mode:

```bash
python -m demos.narratives.zombieagent.demo --step
```

`mcp_test_server.py` is an optional upstream MCP stdio server for testing this
tool surface through the real MCP proxy. The main narrative demo uses the Python
executor directly for deterministic terminal output.
