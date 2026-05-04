# VS Code + Copilot Agent Mode with Safe MCP Proxy

## 1) Configure MCP server in VS Code

Use `.vscode/mcp.json`:

```json
{
  "servers": {
    "safe-proxy": {
      "type": "stdio",
      "command": "python",
      "args": [
        "safe_mcp_proxy/server.py",
        "--policy",
        "safe_mcp_proxy/config/jira_policy.yaml",
        "--upstream",
        "python",
        "-m",
        "safe_mcp_proxy.mcp_test_server"
      ]
    }
  }
}
```

## 2) Enable Copilot Agent Mode + MCP

1. Open VS Code settings and ensure MCP server integration is enabled for Copilot Agent Mode.
2. Open Copilot Chat.
3. Switch to **Agent** mode.
4. Confirm `safe-proxy` server is connected.

## 3) Verify `tools/list` and shaping

Run the proxy directly to inspect logs:

```bash
python safe_mcp_proxy/server.py --policy safe_mcp_proxy/config/jira_policy.yaml --upstream python -m safe_mcp_proxy.mcp_test_server
```

When Copilot starts a session, the proxy serves `tools/list` from downstream, filtered by policy. Forbidden tools are not exposed.

## 4) Demo scenario

Prompt in Copilot Agent mode:

> Update my Jira issues

Expected with proxy:
- query gets constrained to: `assignee = currentUser() AND status = 'Open'`
- forbidden tools (for example `delete_issue`) are denied deterministically

To test deny behavior explicitly, call a denied action; response includes:

```json
{"error": "POLICY_DENY", "tool": "delete_issue", "reason": "tool is explicitly denied"}
```

## 5) Optional simulate mode

Set `simulate: true` in `safe_mcp_proxy/config/jira_policy.yaml`.
Denied tools return deterministic simulated response instead of forwarding.
