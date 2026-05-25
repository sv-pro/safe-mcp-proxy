# MCPZero Demo

MCPZero runs the same attack corpus twice:

1. Baseline mode: direct tool access, no policy enforcement.
2. Protected mode: tool calls routed through safe-mcp-proxy.

The demo passes when an attack succeeds in baseline and is blocked by the proxy.

Run all scenarios:

```bash
python -m mcpzero.demo
```

Compatibility launcher from the canonical demo tree:

```bash
python -m demos.mcpzero.demo
```

Run one scenario:

```bash
python -m mcpzero.demo --scenario email_injection
```

The attack inputs live in `attacks/`; that directory is shared corpus data, not
a runnable demo folder.

Notebook assets live in `notebooks/`. `notebooks/archive/` contains older local
walkthrough copies that were previously scattered under `docs/notebooks/`.
