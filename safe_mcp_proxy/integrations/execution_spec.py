from __future__ import annotations

from dataclasses import dataclass

from safe_mcp_proxy.decision import Decision
from safe_mcp_proxy.integrations.intent_ir import IntentIR
from safe_mcp_proxy.provenance import Provenance


@dataclass(frozen=True)
class ExecutionSpec:
    """Typed policy-evaluation result for a single Gemini tool invocation.

    Produced by GeminiPolicyGate.evaluate() after consulting the PolicyEngine.
    Sits between IntentIR mapping and execution routing (Issue #93).

    Fields:
        decision  — ALLOW / DENY / ABSENT / ASK
        rule      — the specific rule that produced the decision
        intent    — the resolved IntentIR this spec was built from
        provenance — taint / source / mode context that influenced the decision
    """

    decision: Decision
    rule: str
    intent: IntentIR
    provenance: Provenance
