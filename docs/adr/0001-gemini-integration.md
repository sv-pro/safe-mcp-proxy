# ADR 0001 — Gemini Integration as Proxy-Based Enforcement Layer

**Status:** Accepted  
**Date:** 2026-05-02  
**EPIC:** 8 / Gemini Integration

---

## Decision

Introduce Gemini Agent Platform integration as a proxy-based enforcement layer,
not as a feature add-on or SDK wrapper.

---

## Context

Agent platforms expand the capability surface available to LLM agents. Without
governance, an agent can invoke any tool the platform exposes. Agent Hypervisor
/ Safe MCP Proxy acts as a mandatory in-path control plane that constrains the
tool surface to only what the World Manifest declares.

> "Agent platforms expand capability surface.  
> Agent Hypervisor constrains it."

> "Gemini decides what to do.  
> Agent Hypervisor decides what is possible."

The integration is additive — Gemini is unchanged. Only the execution path is
governed.

---

## Architecture

```
Gemini Agent
    │
    ▼
Safe MCP Proxy (Agent Hypervisor)
    │  ┌────────────────────────────────────────────────┐
    │  │  GeminiAdapter → IntentMapper → PolicyGate     │
    │  │  SessionManifestBinder (agent → world)         │
    │  │  GeminiTraceLogger (append-only JSONL trace)   │
    │  └────────────────────────────────────────────────┘
    ▼
Real Tools / APIs
```

---

## Key Design Statements

- **Ontological absence, not soft denial.** A tool that is not in the world
  manifest does not exist from the agent's perspective. The response is
  `"Action does not exist in this world"`, not an error or a refusal.

- **No logic in the LLM path.** All enforcement is deterministic, manifest-
  driven, and capability-based. No LLM is involved in the enforcement path.

- **Session binding is mandatory for multi-agent deployments.**
  `SessionManifestBinder` maps `agent_id` to `world_id` at the request
  boundary. A missing mapping falls back to the most restrictive world — it
  never grants more capability.

- **Audit trail is append-only.** Every decision (ALLOW / DENY / ABSENT / ASK)
  is written to `audit.jsonl`. The Gemini-specific pipeline additionally writes
  a richer 5-stage trace to `data/traces/gemini_trace.jsonl`.

---

## Consequences

- Gemini operates in a smaller, controlled world.
- All undefined actions are absent — not denied.
- Enforcement is deterministic and auditable.
- No LLM is involved in the enforcement path.
- Multiple Gemini agents can coexist with different worlds via `SessionManifestBinder`.
- Executors are cached per `world_id` — manifest parsing happens once per world.

---

## Non-Goals

- Full Gemini SDK integration
- UI / dashboard
- Multi-agent orchestration (beyond `SessionManifestBinder`)
- Performance optimisation (request throughput, latency)

---

## Files

| File | Role |
|------|------|
| `safe_mcp_proxy/integrations/gemini_adapter.py` | Parse Gemini `functionCall` JSON → `ToolCall` |
| `safe_mcp_proxy/integrations/gemini_proxy.py` | Orchestrate pipeline; route decisions |
| `safe_mcp_proxy/integrations/gemini_policy_gate.py` | Evaluate `IntentIR` against policy |
| `safe_mcp_proxy/integrations/intent_ir.py` | Map `ToolCall` → `IntentIR` via registry |
| `safe_mcp_proxy/integrations/execution_spec.py` | Typed policy evaluation result |
| `safe_mcp_proxy/integrations/session_binder.py` | agent_id → world_id → Executor binding |
| `safe_mcp_proxy/integrations/gemini_trace.py` | Append-only 5-stage JSONL trace |
| `worlds/gemini_demo.yaml` | Restricted demo world (EPIC 8 demo) |
| `demos/integrations/gemini/demo.py` | Runnable architectural difference proof |
