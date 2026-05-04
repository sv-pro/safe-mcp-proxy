# Atlassian MCP Proxy — 5-minute quickstart

This guide walks through the attack-and-block demo. No real Atlassian
credentials needed — the proxy runs in stub mode.

## 1. Install dependencies (30 seconds)

```bash
pip install pyyaml fastapi "uvicorn[standard]"
```

## 2. Start the proxy (10 seconds)

```bash
uvicorn api.main:app --reload
```

The proxy starts at `http://localhost:8000`. Check the active config:

```bash
curl -s http://localhost:8000/atlassian/config | python -m json.tool
```

Expected output (stub mode — no upstream required):

```json
{
  "mode": "proxy",
  "upstream_configured": false,
  "timeout": 30,
  "manifest_configured": false,
  "source_channel": "cli"
}
```

## 3. See the demo scenarios (3 minutes)

Run the full attack-and-block scenario as a self-contained script:

```bash
python -m demos.integrations.atlassian.demo
```

**PATH A — no proxy:** the agent reads raw Confluence content (with
credentials in it) and immediately writes it to Jira. No policy gate, no
block. The output shows `CREDENTIALS LEAKED`.

**PATH B — with proxy:** the same sequence is policy-gated:

1. `confluence_get_page` is allowed — but the response is **truncated to
   500 characters** (safe abstraction) and the session is tagged
   `confluence_raw`.
2. `jira_create_issue` is **DENY** (`no_raw_confluence_to_jira`) because
   the flow context carries `confluence_raw`.

The output shows `BLOCKED`.

## 4. Call the proxy manually (1 minute)

**Allowed call** — read a Jira issue:

```bash
curl -s -X POST http://localhost:8000/atlassian/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call",
       "params":{"name":"jira_get_issue","arguments":{"issue_key":"PROJ-1"}}}' \
  | python -m json.tool
```

**Blocked call** — tool not in allowlist (ABSENT):

```bash
curl -s -X POST http://localhost:8000/atlassian/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call",
       "params":{"name":"jira_bulk_delete","arguments":{}}}' \
  | python -m json.tool
```

Response:

```json
{
  "error": {
    "code": -32601,
    "message": "Action does not exist in this world: 'jira_bulk_delete'",
    "data": {"decision": "ABSENT", "rule": "tool_not_allowlisted"}
  }
}
```

## 5. Inspect the audit log

```bash
# All recent decisions
python -m safe_mcp_proxy.atlassian.cli list --last 10

# Only blocked calls
python -m safe_mcp_proxy.atlassian.cli list --decision DENY

# Decision stats
python -m safe_mcp_proxy.atlassian.cli stats

# Full trace for one request
python -m safe_mcp_proxy.atlassian.cli trace --trace-id <trace_id>
```

## Docker

```bash
cp .env.example .env
# Edit .env — set ATLASSIAN_MCP_URL for a real upstream, or leave empty for stub mode

docker build -t safe-mcp-proxy .
docker run --env-file .env -p 8000:8000 safe-mcp-proxy
```

## Connect a real Atlassian upstream

1. Set `ATLASSIAN_MCP_URL` to your Atlassian Remote MCP Server URL.
2. Set `ATLASSIAN_MANIFEST_PATH` to an absolute path of your manifest YAML
   (start with `manifests/atlassian_mvp.yaml` and customize).
3. Set `ATLASSIAN_SOURCE_CHANNEL=web` if requests come from web/email
   contexts (enables taint-based write blocking).
4. Restart the proxy.

All policy enforcement is transparent — the agent sees standard MCP
JSON-RPC responses, with blocked calls returning a JSON-RPC error.
