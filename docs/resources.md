# Resources

A curated collection of publications, docs, and projects in the spirit of safe-mcp-proxy:
control planes, supply-chain security, policy enforcement, and trust boundaries for AI agents.

---

## MCP & Agent Security

### [Control MCP server access for your organization](https://code.claude.com/docs/en/managed-mcp)
*Claude Code — official docs · added 2026-05-26*

Anthropic's official mechanism for enterprise-level control over MCP servers in Claude Code.
Covers `managed-mcp.json` (a fixed server set with exclusive control),
URL- and command-based allowlists/denylists, the `allowManagedMcpServersOnly` flag for blocking
user extensions, and monitoring via OpenTelemetry.
Solves the same problem as safe-mcp-proxy but at the deployment-policy layer rather than the
executable-proxy layer: Managed MCP defines *what is allowed to run*; safe-mcp-proxy defines
*what is allowed to be called, and under what conditions*.

---

### [ClawPatrol](https://clawpatrol.dev/) · [GitHub](https://github.com/denoland/clawpatrol)
*Deno Land · added 2026-05-26*

A security firewall for AI agents from Deno: intercepts and validates an agent's network traffic
before it reaches target systems. Sits between the agent and downstream services, evaluating
requests against rules written in HCL + CEL expressions. Operates at the protocol level —
Kubernetes API, SQL, HTTP — and can block specific operations (e.g. DELETE on a particular table
or deletion of a k8s resource). Deploys as a gateway proxy, a per-process tunnel, or a host
tunnel over WireGuard. The approach differs from safe-mcp-proxy: where safe-mcp-proxy enforces
policy decisions at the MCP tool-call layer, ClawPatrol enforces controls at the wire-protocol
level of outbound network traffic.

---

### [Secure MCP Tunnels](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
*OpenAI API docs · added 2026-05-27*

OpenAI's official guide for securely exposing local MCP servers to the OpenAI platform over
authenticated HTTPS tunnels. The `openai mcp tunnel` CLI command starts a persistent tunnel
that wraps a stdio-based MCP server in an HTTP transport and forwards traffic through OpenAI's
tunnel infrastructure, eliminating the need to self-host a public endpoint. Authentication is
enforced via OAuth 2.0 so only the owning OpenAI account can reach the tunnel. Directly
relevant to safe-mcp-proxy: tunnels solve the *connectivity* problem (how a remote LLM reaches
a local server), while safe-mcp-proxy solves the *authorization* problem (which tools within
that server are callable, under what taint conditions, and with what approval requirements).
The two layers compose naturally — safe-mcp-proxy can sit in front of any tunnel endpoint.

---

### [Announcing Agent Governance Toolkit MCP Extensions for .NET](https://devblogs.microsoft.com/dotnet/announcing-agent-governance-toolkit-mcp-extensions-for-dotnet/)
*Microsoft .NET Blog · added 2026-05-26*

Microsoft has released a preview of the `Microsoft.AgentGovernance.Extensions.ModelContextProtocol`
package — a governance overlay for the official MCP C# SDK that adds governance with a single
`WithGovernance(…)` call on `IMcpServerBuilder`. Covers three layers: tool scanning at server
startup (a hard gate — if a tool fails, the server does not start), runtime policy enforcement
on every tool call, and response sanitization.
Part of the broader [Agent Governance Toolkit](https://github.com/microsoft/agent-governance-toolkit) —
the first open-source framework addressing all 10 risks in the OWASP Agentic Top 10.
A conceptual counterpart of safe-mcp-proxy in the .NET ecosystem: deterministic, sub-millisecond
control over which tools are visible, which are executed, and what they return.

---
