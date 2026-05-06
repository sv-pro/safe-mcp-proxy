# `demos/narratives/zombieagent/`

Narrative terminal demo for support-ticket taint tracking.

## Story

1. A clean support ticket is processed normally.
2. A poisoned ticket causes the agent to read customer records and attempt
   exfiltration through `http_post` and `send_email`; both external side effects
   are denied because provenance is tainted.
3. The world switches from `zombieagent_default` to `zombieagent_lockdown`, and
   exfiltration tools become absent from the tool surface.

## Files

| File | Purpose |
|------|---------|
| `demo.py` | Rich terminal narrative using the Python executor API |
| `run.sh` | Convenience launcher; installs/checks `rich`, optionally starts dashboard |
| `mcp_test_server.py` | Optional upstream MCP stdio server for real proxy testing |
| `data/` | Demo tickets and customer records |

Run:

```bash
bash demos/narratives/zombieagent/run.sh
```

Step-through:

```bash
python -m demos.narratives.zombieagent.demo --step
```

Legacy wrappers at `demos/run_demo.py`, `demos/run_demo.sh`, and
`demos/mcp_test_server.py` delegate here.
