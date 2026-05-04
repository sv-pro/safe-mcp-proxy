# Claude Code Integration — Quickstart

Safe MCP Proxy sits between Claude Code and your tools, enforcing a world manifest policy on every tool call.

```
Claude Code  →  safe-mcp-proxy  →  upstream MCP server
               (policy gate)
```

## 5-minute setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Connect Claude Code

The repo ships with `.mcp.json` — Claude Code picks it up automatically when you open the project folder.

Verify the server is registered:

```bash
claude mcp list
```

You should see `safe-mcp-proxy` in the list.

### 3. Select a world

The default world (`world_manifest.yaml`) exposes `read_file`, `list_repo`, `send_email`, and `send_me_email`.

Switch to a restrictive world:

```bash
# In .mcp.json, change --world default  →  --world read_only
```

Or start the server manually with any world:

```bash
python -m safe_mcp_proxy.mcp_server --world read_only
```

### 4. Add a real upstream (optional)

To proxy through to the bundled test server:

```bash
python -m safe_mcp_proxy.mcp_server \
  --world default \
  --upstream python -m safe_mcp_proxy.mcp_test_server
```

The `safe-mcp-proxy-with-upstream` entry in `.mcp.json` already has this wired.

### 5. Run the demo

```bash
python -m demos.integrations.claude_code.demo
```

Expected output:

```
1. TOOL SURFACE CONTROL  → different worlds expose different tool lists
2. TAINT BLOCKING        → web-sourced payload blocked on send_email (DENY)
3. ABSENT TOOLS          → send_email raises MCP error in read_only world
```

---

## How it works

Every `tools/call` from Claude Code passes through:

```
tools/call
  → Provenance(source_channel="cli")
  → executor.execute()   ← policy_engine.decide()
       ALLOW  → upstream.call_tool() or mock result
       DENY   → McpError("DENY: <rule>")
       ABSENT → McpError("ABSENT: tool_not_allowlisted")
       ASK    → McpError with approval token (INTERACTIVE mode)
  → audit.jsonl          ← every decision logged
```

## Worlds

| World | Description |
|-------|-------------|
| `default` | Standard world from `world_manifest.yaml` |
| `read_only` | Read-only; no external side effects |
| `gemini_demo` | Gemini EPIC demo world |
| `mcpzero_demo` | MCPZero attack demo world |

## CLI reference

```bash
python -m safe_mcp_proxy.mcp_server --help

options:
  --world WORLD_ID       World manifest to load (default: world_manifest.yaml)
  --upstream CMD...      Upstream MCP server command to forward ALLOW'd calls
  --mode interactive     ASK creates approval token (default)
  --mode background      ASK collapses to DENY (autonomous agents)
```

## VS Code

Coming in EPIC 13 — same server binary, different config file (`.vscode/mcp.json`).
