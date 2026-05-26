# Resources

A curated collection of publications, docs, and projects in the spirit of safe-mcp-proxy:
control planes, supply-chain security, policy enforcement, and trust boundaries for AI agents.

---

## MCP & Agent Security

### [Control MCP server access for your organization](https://code.claude.com/docs/en/managed-mcp)
*Claude Code — official docs · добавлено 2026-05-26*

Официальный механизм Anthropic для корпоративного контроля над MCP-серверами в Claude Code.
Описывает `managed-mcp.json` (фиксированный набор серверов с исключительным контролем),
allowlist/denylist по URL и команде, флаг `allowManagedMcpServersOnly` для блокировки
пользовательских расширений, мониторинг через OpenTelemetry.
Решает ту же задачу, что и safe-mcp-proxy, но на уровне политики развёртывания, а не
на уровне исполняемого прокси: Managed MCP — «что разрешено запустить», safe-mcp-proxy —
«что разрешено вызвать и при каких условиях».

---
