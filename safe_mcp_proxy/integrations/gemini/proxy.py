from __future__ import annotations

from typing import Optional

from safe_mcp_proxy.decision import Decision
from safe_mcp_proxy.executor import Executor
from safe_mcp_proxy.integrations.gemini.adapter import GeminiAdapter
from safe_mcp_proxy.integrations.gemini.policy_gate import GeminiPolicyGate
from safe_mcp_proxy.integrations.gemini.trace import GeminiTraceLogger
from safe_mcp_proxy.integrations.gemini.intent_ir import IntentIRError, IntentMapper
from safe_mcp_proxy.provenance import Provenance
from safe_mcp_proxy.simulate import simulate_external_action

_ABSENCE_MESSAGE = "Action does not exist in this world"


class GeminiProxy:
    """Routes a Gemini function-call request through the executor pipeline.

    Request flow:
        GeminiAdapter.parse()       →  ToolCall
        IntentMapper.map()          →  IntentIR   (IntentIRError → ontological absence)
        GeminiPolicyGate.evaluate() →  ExecutionSpec
        executor.execute()          →  result + audit log  (ALLOW / ASK)
        executor.execute()          →  ABSENT result + audit log  (allowlist miss)
        short-circuit               →  DENY response (logged via record_denial)
        short-circuit               →  SIMULATE response (logged via record_simulation)
    """

    def __init__(
        self,
        executor: Executor,
        trace_logger: Optional[GeminiTraceLogger] = None,
    ) -> None:
        self._executor = executor
        self._mapper = IntentMapper(executor.registry)
        self._policy_gate = GeminiPolicyGate(executor)
        self._trace = trace_logger

    def execute(self, request: dict) -> dict:
        tool_call = GeminiAdapter.parse(request)
        source = tool_call.metadata.get("source_channel", "web")
        provenance = Provenance.from_source(source)
        world_id = self._executor.world_id

        if self._trace:
            self._trace.record(
                stage="request",
                tool=tool_call.tool_name,
                taint=provenance.tainted,
                source_channel=source,
                world_id=world_id,
                agent_id=tool_call.agent_id,
                session_id=tool_call.session_id,
                raw=request,
            )
            self._trace.record(
                stage="tool_call",
                tool=tool_call.tool_name,
                taint=provenance.tainted,
                source_channel=source,
                world_id=world_id,
                agent_id=tool_call.agent_id,
                session_id=tool_call.session_id,
                arguments=tool_call.arguments,
            )

        try:
            intent = self._mapper.map(tool_call)
        except IntentIRError:
            # Action is completely unknown — not in any world's catalog.
            if self._trace:
                self._trace.record(
                    stage="absent",
                    tool=tool_call.tool_name,
                    taint=provenance.tainted,
                    source_channel=source,
                    world_id=world_id,
                    agent_id=tool_call.agent_id,
                    session_id=tool_call.session_id,
                    rule="action_not_in_ontology",
                )
            self._executor.record_absence(
                tool_name=tool_call.tool_name,
                rule="action_not_in_ontology",
                source_channel=provenance.source_channel,
                taint=provenance.tainted,
            )
            result = {
                "decision": "ABSENT",
                "rule": "action_not_in_ontology",
                "message": _ABSENCE_MESSAGE,
                "result": None,
            }
            return GeminiAdapter.format_response(tool_call.tool_name, result)

        if self._trace:
            self._trace.record(
                stage="intent",
                tool=intent.action,
                taint=provenance.tainted,
                source_channel=source,
                world_id=world_id,
                side_effect_type=intent.side_effect_type,
                required_capabilities=intent.required_capabilities,
            )

        spec = self._policy_gate.evaluate(intent, provenance)

        if self._trace:
            self._trace.record(
                stage="policy",
                tool=intent.action,
                taint=provenance.tainted,
                source_channel=source,
                world_id=world_id,
                decision=spec.decision.value,
                rule=spec.rule,
            )

        if spec.decision == Decision.DENY:
            self._executor.record_denial(
                tool_name=intent.action,
                rule=spec.rule,
                source_channel=provenance.source_channel,
                taint=provenance.tainted,
            )
            result = {
                "decision": spec.decision.value,
                "rule": spec.rule,
                "message": f"Action blocked by policy: {spec.rule}",
                "result": None,
            }
            return GeminiAdapter.format_response(tool_call.tool_name, result)

        if spec.decision == Decision.SIMULATE:
            self._executor.record_simulation(
                tool_name=intent.action,
                rule=spec.rule,
                source_channel=provenance.source_channel,
                taint=provenance.tainted,
            )
            result = {
                "decision": Decision.SIMULATE.value,
                "rule": spec.rule,
                "simulated": True,
                "result": simulate_external_action(),
            }
            if self._trace:
                self._trace.record(
                    stage="execution",
                    tool=intent.action,
                    taint=provenance.tainted,
                    source_channel=source,
                    world_id=world_id,
                    decision=Decision.SIMULATE.value,
                    rule=spec.rule,
                    simulated=True,
                )
            return GeminiAdapter.format_response(tool_call.tool_name, result)

        # ABSENT (allowlist miss), ALLOW, ASK: delegate to executor.
        # The executor handles execution, ASK token creation, and audit logging.
        result = self._executor.execute(intent.action, intent.parameters, provenance)

        if self._trace:
            self._trace.record(
                stage="execution",
                tool=intent.action,
                taint=provenance.tainted,
                source_channel=source,
                world_id=world_id,
                decision=result.get("decision"),
                rule=result.get("rule"),
            )

        return GeminiAdapter.format_response(tool_call.tool_name, result)

    def list_tools(self) -> dict:
        """Return the manifest-filtered tool surface in Gemini function-declaration format.

        Only tools in the world allowlist are visible — absent tools are not
        mentioned, consistent with the ABSENT principle.
        """
        tools = self._executor.registry.list_exposed()
        return {
            "tools": [
                {"name": tool.name, "parameters": tool.schema}
                for tool in tools
            ]
        }
