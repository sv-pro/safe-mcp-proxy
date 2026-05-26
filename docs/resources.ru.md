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

### [ClawPatrol](https://clawpatrol.dev/) · [GitHub](https://github.com/denoland/clawpatrol)
*Deno Land · добавлено 2026-05-26*

Security firewall для AI-агентов от Deno: перехватывает и валидирует сетевой трафик агента
до того, как он достигает целевых систем. Сидит между агентом и сервисами, анализируя
запросы по правилам на HCL + CEL-выражениях. Умеет работать на уровне протокола —
Kubernetes API, SQL, HTTP — и блокировать конкретные операции (например, DELETE на
определённую таблицу или удаление ресурса в k8s). Деплоится как gateway-прокси,
per-process туннель или хостовый туннель через WireGuard. Подход к проблеме другой:
если safe-mcp-proxy контролирует вызовы MCP-инструментов на уровне решений политики,
ClawPatrol контролирует исходящий сетевой трафик на уровне wire-протокола.

---

### [Announcing Agent Governance Toolkit MCP Extensions for .NET](https://devblogs.microsoft.com/dotnet/announcing-agent-governance-toolkit-mcp-extensions-for-dotnet/)
*Microsoft .NET Blog · добавлено 2026-05-26*

Microsoft открыла превью пакета `Microsoft.AgentGovernance.Extensions.ModelContextProtocol` —
надстройки над официальным MCP C# SDK, которая добавляет governance одним вызовом
`WithGovernance(…)` на `IMcpServerBuilder`. Покрывает три слоя: сканирование инструментов
при старте сервера (жёсткий gate — если инструмент не прошёл, сервер не запускается),
runtime policy enforcement на каждый tool call, и санитизацию ответов.
Часть более широкого [Agent Governance Toolkit](https://github.com/microsoft/agent-governance-toolkit) —
первого open-source фреймворка, закрывающего все 10 рисков OWASP Agentic Top 10.
Идейный аналог safe-mcp-proxy в экосистеме .NET: детерминированный, sub-millisecond контроль
над тем, какие инструменты видны, выполняются и что возвращают.

---
