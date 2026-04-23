# safe_mcp_proxy/policies/proxy.rego
#
# Canonical Rego policy for safe-mcp-proxy.
#
# Input schema (all fields required):
#   input.tool_name           string  — name of the requested tool
#   input.capability          string  — capability key declared for the tool
#   input.taint               boolean — true when request originates from an untrusted channel
#   input.side_effect_type    string  — "external" | "internal" | "read" | "unknown"
#   input.descriptor_hash_valid boolean — true when current schema hash matches the pinned hash
#   input.allowlist           array   — tool names permitted in this world
#   input.capability_map      object  — capability → boolean (allowed flag)
#
# Output: data.safe_mcp_proxy.decision
#   { "decision": "ALLOW" | "DENY" | "ABSENT", "rule": "<rule_hit>" }
#
# Decision priority (mirrors policy_engine.py ordering):
#   1. ABSENT / tool_not_allowlisted
#   2. ABSENT / capability_not_allowed
#   3. DENY   / descriptor_drift
#   4. DENY   / tainted_external_side_effect
#   5. ALLOW  / default_allow

package safe_mcp_proxy

default decision = {"decision": "ALLOW", "rule": "default_allow"}

# Rule 1: tool not in the allowlist → ABSENT
decision = {"decision": "ABSENT", "rule": "tool_not_allowlisted"} if {
	not _tool_allowlisted
}

# Rule 2: capability flag is disabled → ABSENT
# Only evaluated when the tool is allowlisted (lower priority than rule 1).
decision = {"decision": "ABSENT", "rule": "capability_not_allowed"} if {
	_tool_allowlisted
	not _capability_allowed
}

# Rule 3: descriptor hash mismatch → DENY
# Only evaluated when tool is allowlisted and capability is enabled.
decision = {"decision": "DENY", "rule": "descriptor_drift"} if {
	_tool_allowlisted
	_capability_allowed
	not input.descriptor_hash_valid
}

# Rule 4: tainted source attempting an external side effect → DENY
# Only evaluated when the tool is allowlisted, capability enabled, and hash is valid.
decision = {"decision": "DENY", "rule": "tainted_external_side_effect"} if {
	_tool_allowlisted
	_capability_allowed
	input.descriptor_hash_valid
	input.taint == true
	input.side_effect_type == "external"
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_tool_allowlisted if {
	input.tool_name == input.allowlist[_]
}

_capability_allowed if {
	input.capability_map[input.capability] == true
}
