import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union

from safe_mcp_proxy.approval_store import ApprovalStore
from safe_mcp_proxy.capability_projection import CapabilityProjectionEngine, ProjectionContext, ProjectionResult
from safe_mcp_proxy.compiler import SkillCapabilityConfig
from safe_mcp_proxy.decision import Decision
from safe_mcp_proxy.descriptor import compute_descriptor_hash, descriptor_hash_valid
from safe_mcp_proxy.execution_mode import ExecutionMode
from safe_mcp_proxy.policy_engine import PolicyEngine
from safe_mcp_proxy.provenance import Provenance
from safe_mcp_proxy.registry import Tool, ToolRegistry
from safe_mcp_proxy.simulate import simulate_external_action

if TYPE_CHECKING:
    from safe_mcp_proxy.world_controller import WorldController

ABSENT_MESSAGE = "Action does not exist in this world"


def _validate_constraints(constraints: Dict[str, Any], payload: Dict[str, Any]) -> Tuple[bool, str]:
    """Validate payload against declared capability constraints.

    Returns (True, "") when all constraints pass, (False, reason_code) on first violation.
    """
    if not constraints:
        return True, ""

    max_bytes = constraints.get("max_bytes_billed")
    if max_bytes is not None:
        if payload.get("bytes_billed", 0) > max_bytes:
            return False, "constraint_violation_bytes_billed"

    for pattern in constraints.get("deny_patterns", []):
        for v in payload.values():
            if isinstance(v, str) and pattern in v:
                return False, "constraint_violation_deny_pattern"

    allowed_domains = constraints.get("allowed_domains", [])
    if allowed_domains:
        email_val = str(payload.get("to") or payload.get("email") or "")
        if email_val:
            domain = email_val.split("@")[-1] if "@" in email_val else ""
            if not any(domain == d or email_val.endswith("@" + d) for d in allowed_domains):
                return False, "constraint_violation_domain"

    return True, ""


class Executor:
    def __init__(
        self,
        registry: ToolRegistry,
        policy_engine: PolicyEngine,
        audit_log_path: str,
        simulate_external: bool = False,
        approval_store: Optional[ApprovalStore] = None,
        projection_engine: Optional[CapabilityProjectionEngine] = None,
        skill_capabilities: Optional[Dict[str, SkillCapabilityConfig]] = None,
        world_id: str = "",
        policy_version: str = "",
        world_controller: Optional["WorldController"] = None,
        base_dir: Optional[Path] = None,
    ):
        self.registry = registry
        self.policy_engine = policy_engine
        self.simulate_external = simulate_external
        self.audit_log_path = Path(audit_log_path)
        self.approval_store = approval_store or ApprovalStore()
        self.projection_engine = projection_engine
        self.skill_capabilities: Dict[str, SkillCapabilityConfig] = skill_capabilities or {}
        self._stored_world_id = world_id
        self.policy_version = policy_version
        self.world_controller = world_controller
        self._base_dir = base_dir

    # ------------------------------------------------------------------
    # world_id — reads from WorldController when present
    # ------------------------------------------------------------------

    @property
    def world_id(self) -> str:
        if self.world_controller is not None:
            return self.world_controller.current_id()
        return self._stored_world_id

    # ------------------------------------------------------------------
    # Dynamic world resolution
    # ------------------------------------------------------------------

    def _build_policy_for_world(self, world: Dict[str, Any]) -> "PolicyEngine":
        """Build a policy engine from a compiled world dict."""
        approval_required = world.get("approval_required", [])
        engine_name = world.get("policy_engine", "python")
        if engine_name == "opa" and self._base_dir:
            from safe_mcp_proxy.opa_engine import OPAPolicyEngine
            policy_path = str(self._base_dir / "safe_mcp_proxy" / "policies" / "proxy.rego")
            return OPAPolicyEngine(  # type: ignore[return-value]
                policy_path=policy_path,
                allowlist=world["allowlist"],
                capability_map=world["capability_map"],
                approval_required=approval_required,
            )
        return PolicyEngine(
            allowlist=world.get("allowlist", []),
            capability_map=world.get("capability_map", {}),
            approval_required=approval_required,
        )

    def _resolve_components(self) -> Tuple[ToolRegistry, "PolicyEngine", str]:
        """Return (registry, policy_engine, world_id) for the current call.

        When WorldController is present we keep using the stored registry so
        that in-memory mutations (e.g. descriptor-drift tests that corrupt a
        tool schema) are still detected.  Only the policy engine is rebuilt
        from the current world on every call so that world switches take effect
        immediately without rebuilding the full tool catalog.
        """
        if self.world_controller is not None:
            world = self.world_controller.world
            wid = self.world_controller.current_id()
            policy_engine = self._build_policy_for_world(world)
            return self.registry, policy_engine, wid  # type: ignore[return-value]
        return self.registry, self.policy_engine, self._stored_world_id

    # ------------------------------------------------------------------
    # list_tools (projection-based, for skill capabilities)
    # ------------------------------------------------------------------

    def list_tools(self, context: ProjectionContext) -> ProjectionResult:
        """Return projected skill capabilities for the given execution context."""
        if not self.projection_engine or not self.skill_capabilities:
            result = ProjectionResult(visible=[], hidden=[])
        else:
            result = self.projection_engine.project(self.skill_capabilities, context)
        self._audit(
            tool="list_tools",
            decision="ALLOW",
            rule="projection",
            taint=False,
            descriptor_hash="",
            source_channel="",
            policy_version=self.policy_version,
            identity=context.identity,
            workflow_id=context.workflow_id,
            mode=context.mode.value,
            visible_count=len(result.visible),
            hidden_count=len(result.hidden),
        )
        return result

    # ------------------------------------------------------------------
    # Skill execution
    # ------------------------------------------------------------------

    def execute_skill(
        self,
        tool_name: str,
        payload: Dict[str, Any],
        context: ProjectionContext,
        provenance: Provenance,
    ) -> Dict[str, Any]:
        """Execution guard for skill-backed capabilities."""
        source_provenance = [provenance.source_channel] if provenance.source_channel else []
        extra: Dict[str, Any] = {
            "policy_version": self.policy_version,
            "identity": context.identity,
            "workflow_id": context.workflow_id,
            "mode": context.mode.value,
            "source_provenance": source_provenance,
            "side_effect": "",
        }

        cap = self.skill_capabilities.get(tool_name)
        if cap is None:
            return self._skill_deny(tool_name, "capability_not_defined", provenance, **extra)

        extra["side_effect"] = cap.side_effect

        if cap.allowed is False:
            return self._skill_deny(tool_name, "capability_not_allowed", provenance, **extra)

        if self.projection_engine:
            side_effect_reason = self.projection_engine.side_effect_denial(cap, context)
            if side_effect_reason:
                return self._skill_deny(tool_name, "capability_not_visible", provenance,
                                        detail=side_effect_reason, **extra)

        if cap.provenance_required and provenance.tainted:
            return self._skill_deny(tool_name, "provenance_violation", provenance, **extra)

        if cap.requires_approval and tool_name not in context.approved_capabilities:
            self._audit(
                tool=tool_name,
                decision="ASK",
                rule="approval_required",
                taint=provenance.tainted,
                descriptor_hash="",
                source_channel=provenance.source_channel,
                **extra,
            )
            return {"decision": "ASK", "rule": "approval_required", "result": None}

        valid, constraint_reason = _validate_constraints(cap.constraints, payload)
        if not valid:
            return self._skill_deny(tool_name, constraint_reason, provenance, **extra)

        result = (
            simulate_external_action()
            if self.simulate_external and cap.side_effect not in ("none", "read")
            else {"ok": True, "skill": tool_name}
        )
        self._audit(
            tool=tool_name,
            decision="ALLOW",
            rule="default_allow",
            taint=provenance.tainted,
            descriptor_hash="",
            source_channel=provenance.source_channel,
            **extra,
        )
        return {"decision": "ALLOW", "rule": "default_allow", "result": result}

    def _skill_deny(
        self,
        tool_name: str,
        reason: str,
        provenance: Provenance,
        detail: str = "",
        **extra: Any,
    ) -> Dict[str, Any]:
        self._audit(
            tool=tool_name,
            decision="DENY",
            rule=reason,
            taint=provenance.tainted,
            descriptor_hash="",
            source_channel=provenance.source_channel,
            **extra,
        )
        msg = f"Denied: {reason}" + (f" ({detail})" if detail else "")
        return {"decision": "DENY", "rule": reason, "result": {"error": msg}}

    # ------------------------------------------------------------------
    # Core execute
    # ------------------------------------------------------------------

    def _tool_context(
        self,
        tool_name: str,
        registry: Optional[ToolRegistry] = None,
    ) -> Tuple[Optional[Tool], str, str, bool]:
        reg = registry if registry is not None else self.registry
        tool = reg.get_tool(tool_name)
        capability = tool.capability if tool else tool_name
        side_effect_type = tool.side_effect_type if tool else "unknown"
        hash_ok = descriptor_hash_valid(tool.schema, tool.descriptor_hash) if tool else True
        return tool, capability, side_effect_type, hash_ok

    def execute(self, tool_name: str, payload: Dict[str, Any], provenance: Provenance) -> Dict[str, Any]:
        _registry, _policy_engine, _world_id = self._resolve_components()

        tool, capability, side_effect_type, hash_ok = self._tool_context(tool_name, _registry)
        descriptor_hash = compute_descriptor_hash(tool.schema) if tool else ""

        policy = _policy_engine.decide(
            tool_name=tool_name,
            capability=capability,
            taint=provenance.tainted,
            side_effect_type=side_effect_type,
            descriptor_hash_valid=hash_ok,
        )

        if policy.decision == Decision.ALLOW:
            # `tool` may be None when a world switch added a tool that wasn't in
            # the stored registry's original allowlist.  Fall back to the full
            # catalog so we can still run it (the policy already cleared it).
            exec_tool = tool or _registry.get_any_tool(tool_name)
            if self.simulate_external and exec_tool and exec_tool.side_effect_type == "external":
                response = simulate_external_action()
            elif exec_tool:
                response = exec_tool.handler(payload)
            else:
                response = _registry.execute_tool(tool_name, payload)  # raises if still missing
            self._audit(
                tool=tool_name,
                decision=policy.decision.value,
                rule=policy.rule_hit,
                taint=provenance.tainted,
                descriptor_hash=descriptor_hash,
                source_channel=provenance.source_channel,
                world_id=_world_id,
            )
            return {"decision": policy.decision.value, "rule": policy.rule_hit, "result": response}

        elif policy.decision == Decision.DENY:
            response = {"error": "Denied by policy", "reason": policy.rule_hit}
            self._audit(
                tool=tool_name,
                decision=policy.decision.value,
                rule=policy.rule_hit,
                taint=provenance.tainted,
                descriptor_hash=descriptor_hash,
                source_channel=provenance.source_channel,
                world_id=_world_id,
            )
            return {"decision": policy.decision.value, "rule": policy.rule_hit, "result": response}

        elif policy.decision == Decision.ASK:
            if provenance.execution_mode == ExecutionMode.BACKGROUND:
                effective_rule = "ask_unavailable_in_background"
                response = {"error": "Denied by policy", "reason": effective_rule}
                self._audit(
                    tool=tool_name,
                    decision=Decision.DENY.value,
                    rule=effective_rule,
                    taint=provenance.tainted,
                    descriptor_hash=descriptor_hash,
                    source_channel=provenance.source_channel,
                    world_id=_world_id,
                )
                return {"decision": Decision.DENY.value, "rule": effective_rule, "result": response}
            else:
                token = self.approval_store.create(
                    tool_name=tool_name,
                    payload=payload,
                    source_channel=provenance.source_channel,
                    tainted=provenance.tainted,
                    execution_mode=provenance.execution_mode.value,
                )
                self._audit(
                    tool=tool_name,
                    decision=Decision.ASK.value,
                    rule=policy.rule_hit,
                    taint=provenance.tainted,
                    descriptor_hash=descriptor_hash,
                    source_channel=provenance.source_channel,
                    world_id=_world_id,
                )
                return {
                    "decision": Decision.ASK.value,
                    "rule": policy.rule_hit,
                    "approval_token": token,
                    "result": None,
                }

        else:
            # ABSENT
            response = {"error": ABSENT_MESSAGE}
            self._audit(
                tool=tool_name,
                decision=policy.decision.value,
                rule=policy.rule_hit,
                taint=provenance.tainted,
                descriptor_hash=descriptor_hash,
                source_channel=provenance.source_channel,
                world_id=_world_id,
            )
            return {"decision": policy.decision.value, "rule": policy.rule_hit, "result": response}

    def execute_approved(self, token: str) -> Dict[str, Any]:
        """Execute a previously ASK'd tool after its approval token has been approved."""
        entry = self.approval_store.get(token)
        if entry is None:
            return {"error": "Token not found", "approval_token": token}
        if entry.status != "approved":
            return {"error": f"Token is {entry.status}, not approved", "approval_token": token}

        _registry, _, _world_id = self._resolve_components()

        tool = _registry.get_tool(entry.tool_name)
        descriptor_hash = compute_descriptor_hash(tool.schema) if tool else ""

        if tool is None:
            response = {"error": ABSENT_MESSAGE}
            decision_val, rule_val = Decision.ABSENT.value, "tool_not_allowlisted"
        elif self.simulate_external and tool.side_effect_type == "external":
            response = simulate_external_action()
            decision_val, rule_val = Decision.ALLOW.value, "approved"
        else:
            response = _registry.execute_tool(entry.tool_name, entry.payload)
            decision_val, rule_val = Decision.ALLOW.value, "approved"

        self.approval_store.mark_executed(token)
        self._audit(
            tool=entry.tool_name,
            decision=decision_val,
            rule=rule_val,
            taint=entry.tainted,
            descriptor_hash=descriptor_hash,
            source_channel=entry.source_channel,
            world_id=_world_id,
        )
        return {
            "decision": decision_val,
            "rule": rule_val,
            "approval_token": token,
            "result": response,
        }

    def reject_approval(self, token: str) -> Dict[str, Any]:
        """Record a rejection for a pending approval token."""
        entry = self.approval_store.get(token)
        if entry is None:
            return {"error": "Token not found", "approval_token": token}
        if entry.status != "pending":
            return {"error": f"Token is already {entry.status}", "approval_token": token}

        self.approval_store.reject(token)
        _registry, _, _world_id = self._resolve_components()
        tool = _registry.get_tool(entry.tool_name)
        descriptor_hash = compute_descriptor_hash(tool.schema) if tool else ""

        self._audit(
            tool=entry.tool_name,
            decision=Decision.DENY.value,
            rule="approval_rejected",
            taint=entry.tainted,
            descriptor_hash=descriptor_hash,
            source_channel=entry.source_channel,
            world_id=_world_id,
        )
        return {
            "decision": Decision.DENY.value,
            "rule": "approval_rejected",
            "approval_token": token,
            "result": {"error": "Denied by policy", "reason": "approval_rejected"},
        }

    # ------------------------------------------------------------------
    # Replay
    # ------------------------------------------------------------------

    def replay(self, audit_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Re-evaluate policy for a recorded audit entry.

        Entries written before world_id was recorded (old seeds / live logs)
        will have no world_id key; in that case we fall back to the stored
        registry and policy_engine (the default world for this executor).
        """
        tool_name = audit_entry["tool"]
        tainted = audit_entry["taint"]

        entry_world_id = audit_entry.get("world_id")
        if self.world_controller is not None and entry_world_id:
            # Replay with the world that was active when the entry was recorded.
            try:
                _registry, _policy_engine, _ = self._build_components_for_world(entry_world_id)
            except Exception:
                _registry, _policy_engine = self.registry, self.policy_engine
        else:
            # No world_id in entry (old format) — fall back to default (stored) world.
            _registry, _policy_engine = self.registry, self.policy_engine

        _, capability, side_effect_type, hash_ok = self._tool_context(tool_name, _registry)

        policy = _policy_engine.decide(
            tool_name=tool_name,
            capability=capability,
            taint=tainted,
            side_effect_type=side_effect_type,
            descriptor_hash_valid=hash_ok,
        )

        matches = policy.decision.value == audit_entry["decision"] and policy.rule_hit == audit_entry["rule"]
        return {
            "recorded_decision": audit_entry["decision"],
            "recorded_rule": audit_entry["rule"],
            "replayed_decision": policy.decision.value,
            "replayed_rule": policy.rule_hit,
            "matches": matches,
        }

    def _build_components_for_world(self, world_id: str) -> Tuple[ToolRegistry, "PolicyEngine", str]:
        """Compile a specific world and return its registry + policy engine.

        Used by replay() to re-evaluate a recorded entry against the world
        that was active at the time it was written.
        """
        from safe_mcp_proxy.compiler import compile_world_manifest, resolve_manifest_path
        assert self._base_dir is not None
        path = resolve_manifest_path(self._base_dir, world_id or None)
        world = compile_world_manifest(str(path))
        registry = ToolRegistry.with_mock_tools(
            allowlist=world.get("allowlist", []),
            capability_defs=world.get("capability_definitions"),
        )
        policy_engine = self._build_policy_for_world(world)
        return registry, policy_engine, world.get("world_id", world_id)  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Audit helpers
    # ------------------------------------------------------------------

    def record_absence(self, tool_name: str, rule: str, source_channel: str, taint: bool = False) -> None:
        """Log an ABSENT decision to the audit trail without executing anything."""
        self._audit(
            tool=tool_name,
            decision="ABSENT",
            rule=rule,
            taint=taint,
            descriptor_hash="",
            source_channel=source_channel,
        )

    def record_denial(self, tool_name: str, rule: str, source_channel: str, taint: bool = False) -> None:
        """Log a DENY decision to the audit trail without executing anything."""
        self._audit(
            tool=tool_name,
            decision="DENY",
            rule=rule,
            taint=taint,
            descriptor_hash="",
            source_channel=source_channel,
        )

    def record_simulation(self, tool_name: str, rule: str, source_channel: str, taint: bool = False) -> None:
        """Log a SIMULATE decision to the audit trail without executing anything."""
        self._audit(
            tool=tool_name,
            decision="SIMULATE",
            rule=rule,
            taint=taint,
            descriptor_hash="",
            source_channel=source_channel,
            simulated=True,
        )

    def _audit(
        self,
        tool: str,
        decision: str,
        rule: str,
        taint: bool,
        descriptor_hash: str,
        source_channel: str,
        **extra: Any,
    ) -> None:
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool": tool,
            "decision": decision,
            "rule": rule,
            "taint": taint,
            "descriptor_hash": descriptor_hash,
            "source_channel": source_channel,
        }
        # Always record world_id; callers may pass it explicitly via extra,
        # otherwise fall back to the property (which reads from WorldController).
        if "world_id" not in extra:
            extra["world_id"] = self.world_id
        entry.update(extra)
        with self.audit_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")
