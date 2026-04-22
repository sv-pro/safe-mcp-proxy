from dataclasses import dataclass
from typing import Dict, Iterable, Set


@dataclass(frozen=True)
class PolicyResult:
    decision: str
    rule_hit: str


class PolicyEngine:
    def __init__(self, allowlist: Iterable[str], capability_map: Dict[str, bool]):
        self.allowlist: Set[str] = set(allowlist)
        self.capability_map = dict(capability_map)

    def decide(
        self,
        tool_name: str,
        capability: str,
        taint: bool,
        side_effect_type: str,
        descriptor_hash_valid: bool,
    ) -> PolicyResult:
        if tool_name not in self.allowlist:
            return PolicyResult(decision="ABSENT", rule_hit="tool_not_allowlisted")
        if not self.capability_map.get(capability, False):
            return PolicyResult(decision="ABSENT", rule_hit="capability_not_allowed")
        if not descriptor_hash_valid:
            return PolicyResult(decision="DENY", rule_hit="descriptor_drift")
        if taint and side_effect_type == "external":
            return PolicyResult(decision="DENY", rule_hit="tainted_external_side_effect")
        return PolicyResult(decision="ALLOW", rule_hit="default_allow")
