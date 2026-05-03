# Roadmap

All EPICs 0–11 are implemented. This document captures proposed next directions.

---

## Gemini Integration Phase *(EPIC 8 — completed)*

| Phase | Description |
|-------|-------------|
| Phase 1 | Proxy — passthrough endpoint, no enforcement |
| Phase 2 | Tool surface control — World Manifest-filtered `/tools/list` |
| Phase 3 | Policy enforcement — PolicyEngine wired into execution path |
| Phase 4 | Context binding — agent_id / session_id → manifest mapping |
| Phase 5 | Demo & validation — reproducible exfiltration scenario |

Full issue list: [EPIC 8 label filter](https://github.com/sv-pro/safe-mcp-proxy/labels/epic%2F8-gemini)

---

## Proposed Next Directions

### Real Integration

| Idea | Description |
|------|-------------|
| Live MCP server | **EPIC 12 — in progress.** Real stdio MCP server (`safe_mcp_proxy/mcp_server.py`) using MCP SDK; Claude Code connects via `.mcp.json`; full policy enforcement on every `tools/call`. |
| VS Code integration | **EPIC 13 — next.** Same `mcp_server.py` binary; different config file (`.vscode/mcp.json`). Issue: #165 |
| Real Atlassian MCP upstream | Connect Atlassian passthrough to the actual Atlassian Remote MCP Server; validate all arg_rules and flow_rules against live Jira/Confluence data |

### Policy Depth

| Idea | Description |
|------|-------------|
| `context_ref` in Capability DSL | Complete the third value source in `capability_dsl.py` — currently raises `NotImplementedError`; resolves capability parameters from execution context (user identity, time, workflow state) |
| Policy as Code in CI | GitHub Actions workflow that runs `bundle_replay` against pinned traces on every PR; any policy drift fails the build |
| Policy tuner | Analyze `audit.jsonl` and suggest manifest changes: tools never called → remove from allowlist; repeated taint patterns → tighten rules |

### New LLM Adapters

| Idea | Description |
|------|-------------|
| Claude API adapter | Map Claude `tool_use` blocks → `ToolCall` → executor; reuse existing `session_binder.py` and `GeminiPolicyGate` pattern |
| OpenAI function calling adapter | Map OpenAI `tool_calls` array → same pipeline; same enforcement, different wire format |

### Multi-Agent

| Idea | Description |
|------|-------------|
| Agent-to-agent taint propagation | When agent A calls agent B via a tool, taint must flow across the boundary; `Provenance.derive()` exists but the inter-agent case is unhandled |
| Orchestrator manifest | A manifest type for orchestrators that controls which sub-agents can be invoked and with what capability surface |

### Observability

| Idea | Description |
|------|-------------|
| Trace visualization | HTML or rich-CLI report generated from `audit.jsonl` — shows call tree with taint labels and per-step decisions |
| ASK approval UI | Minimal web UI or interactive CLI prompt for INTERACTIVE mode approvals — currently approval requires a raw REST call to `/approvals/{token}/approve` |

### Research

| Idea | Description |
|------|-------------|
| Ontological confinement benchmark | Run public agent attack datasets (prompt injection, jailbreak corpora) through the proxy; measure and publish block rate vs baselines |
| Signed world manifests | Operator signs the manifest with a private key; proxy verifies signature before loading — closes supply-chain attack vector on the manifest itself |
