# safe-mcp-proxy

Minimal Safe MCP Proxy prototype focused on deterministic control over runtime tool exposure.

## Problem

MCP introduces runtime tool discovery, creating a dynamic supply-chain risk unless tool exposure and execution are constrained.

## Solution

A narrow control plane that:
- wraps a tool registry
- exposes only allowlisted tools
- enforces deterministic policy rules
- tracks taint/provenance
- detects descriptor drift
- writes append-only audit records

## Key idea

> Some actions are denied. Others do not exist.

`ABSENT` means the tool/capability is hidden from this world. `DENY` means a visible action was blocked by policy.

## Architecture

```text
agent
  ↓
Safe MCP Proxy
  ↓
approved MCP servers (mocked adapters)
```

## File layout

```text
safe_mcp_proxy/
  main.py
  registry.py
  descriptor.py
  policy_engine.py
  provenance.py
  executor.py
  simulate.py
  compiler.py
  config/policy.yaml
  examples/
    benign_flow.py
    prompt_injection.py
    poisoned_descriptor.py
    absent_tool_case.py
  logs/audit.jsonl
world_manifest.yaml
```

## Demo

Run from repository root:

```bash
python -m safe_mcp_proxy.examples.benign_flow
python -m safe_mcp_proxy.examples.prompt_injection
python -m safe_mcp_proxy.examples.poisoned_descriptor
python -m safe_mcp_proxy.examples.absent_tool_case
```

Or run directly through CLI entrypoint:

```bash
python -m safe_mcp_proxy.main --tool read_file --source cli --payload '{"path":"README.md"}'
```

Audit records are appended to:

```text
safe_mcp_proxy/logs/audit.jsonl
```
