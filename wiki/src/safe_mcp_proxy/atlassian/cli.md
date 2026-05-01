# `atlassian/cli.py`

## Role

CLI inspector for Atlassian MCP proxy traces. Exposes three commands — `list`, `stats`, `trace` — over the Atlassian-specific JSONL audit log. Invoked via `python -m safe_mcp_proxy.atlassian.cli`.

## Commands

| Command | Description |
|---------|-------------|
| `list` (default) | Print recent decision entries with color-coded decision, tool, rule, tainted, flow labels, trace ID prefix |
| `stats` | Print total decision count and per-decision breakdown |
| `trace` | Print all entries (request + decision + response) for a given `--trace-id` |

## Options

| Option | Description |
|--------|-------------|
| `--log PATH` | Path to JSONL log (default: `safe_mcp_proxy/logs/atlassian_requests.jsonl`) |
| `--decision D` | Filter by decision: `ALLOW`, `DENY`, `ABSENT` |
| `--tool TOOL` | Filter by tool name |
| `--last N` | Show last N decision entries |
| `--trace-id ID` | Trace ID for the `trace` command |

## Depends on

- [[src/safe_mcp_proxy/atlassian/trace_reader]] — `AtlassianTraceReader`

## Used by

Standalone CLI usage only; not imported by other modules.

## See also

- [[src/safe_mcp_proxy/atlassian/trace_reader]] — the data source
- [[src/safe_mcp_proxy/atlassian/index]] — subpackage overview
