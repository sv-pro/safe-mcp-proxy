# safe_mcp_proxy/policies/proxy_test.rego
#
# OPA unit tests for proxy.rego.
# Run with:  opa test safe_mcp_proxy/policies/ -v
#
# Each test mirrors one of the five decision paths in the Python PolicyEngine
# and the corresponding test cases in tests/test_proxy.py.

package safe_mcp_proxy_test

import data.safe_mcp_proxy

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

_base_input := {
	"tool_name": "read_file",
	"capability": "read_file",
	"taint": false,
	"side_effect_type": "read",
	"descriptor_hash_valid": true,
	"allowlist": ["read_file", "list_repo", "send_email"],
	"capability_map": {
		"read_file": true,
		"list_repo": true,
		"send_email": true,
		"dangerous_exec": false,
	},
}

# ---------------------------------------------------------------------------
# Rule 5 (default): ALLOW / default_allow
# ---------------------------------------------------------------------------

test_benign_cli_read_allows if {
	result := safe_mcp_proxy.decision with input as _base_input
	result.decision == "ALLOW"
	result.rule == "default_allow"
}

test_benign_list_repo_allows if {
	inp := object.union(_base_input, {"tool_name": "list_repo", "capability": "list_repo", "side_effect_type": "internal"})
	result := safe_mcp_proxy.decision with input as inp
	result.decision == "ALLOW"
	result.rule == "default_allow"
}

# ---------------------------------------------------------------------------
# Rule 1: ABSENT / tool_not_allowlisted
# ---------------------------------------------------------------------------

test_non_allowlisted_tool_is_absent if {
	inp := object.union(_base_input, {
		"tool_name": "dangerous_exec",
		"capability": "dangerous_exec",
		"side_effect_type": "external",
	})
	result := safe_mcp_proxy.decision with input as inp
	result.decision == "ABSENT"
	result.rule == "tool_not_allowlisted"
}

test_completely_unknown_tool_is_absent if {
	inp := object.union(_base_input, {
		"tool_name": "drop_database",
		"capability": "drop_database",
		"side_effect_type": "external",
	})
	result := safe_mcp_proxy.decision with input as inp
	result.decision == "ABSENT"
	result.rule == "tool_not_allowlisted"
}

# ---------------------------------------------------------------------------
# Rule 2: ABSENT / capability_not_allowed
# ---------------------------------------------------------------------------

test_disabled_capability_is_absent if {
	# send_email is in allowlist but its capability flag is false in this world
	inp := {
		"tool_name": "send_email",
		"capability": "send_email",
		"taint": false,
		"side_effect_type": "external",
		"descriptor_hash_valid": true,
		"allowlist": ["read_file", "list_repo", "send_email"],
		"capability_map": {
			"read_file": true,
			"list_repo": true,
			"send_email": false,
		},
	}
	result := safe_mcp_proxy.decision with input as inp
	result.decision == "ABSENT"
	result.rule == "capability_not_allowed"
}

test_missing_capability_key_is_absent if {
	# capability key not present in map at all → treated as disabled
	inp := {
		"tool_name": "read_file",
		"capability": "read_file",
		"taint": false,
		"side_effect_type": "read",
		"descriptor_hash_valid": true,
		"allowlist": ["read_file"],
		"capability_map": {},
	}
	result := safe_mcp_proxy.decision with input as inp
	result.decision == "ABSENT"
	result.rule == "capability_not_allowed"
}

# ---------------------------------------------------------------------------
# Rule 3: DENY / descriptor_drift
# ---------------------------------------------------------------------------

test_descriptor_drift_is_denied if {
	inp := object.union(_base_input, {"descriptor_hash_valid": false})
	result := safe_mcp_proxy.decision with input as inp
	result.decision == "DENY"
	result.rule == "descriptor_drift"
}

# Drift takes priority over taint (rule 3 < rule 4 in priority, but drift fires first
# because it is checked before taint — both require allowlisted + capability enabled).
test_drift_beats_taint if {
	inp := object.union(_base_input, {
		"tool_name": "send_email",
		"capability": "send_email",
		"side_effect_type": "external",
		"taint": true,
		"descriptor_hash_valid": false,
	})
	result := safe_mcp_proxy.decision with input as inp
	result.decision == "DENY"
	result.rule == "descriptor_drift"
}

# ---------------------------------------------------------------------------
# Rule 4: DENY / tainted_external_side_effect
# ---------------------------------------------------------------------------

test_tainted_external_is_denied if {
	inp := object.union(_base_input, {
		"tool_name": "send_email",
		"capability": "send_email",
		"taint": true,
		"side_effect_type": "external",
		"descriptor_hash_valid": true,
	})
	result := safe_mcp_proxy.decision with input as inp
	result.decision == "DENY"
	result.rule == "tainted_external_side_effect"
}

test_tainted_read_is_allowed if {
	# taint does NOT block non-external side effects
	inp := object.union(_base_input, {"taint": true})
	result := safe_mcp_proxy.decision with input as inp
	result.decision == "ALLOW"
	result.rule == "default_allow"
}

test_clean_external_is_allowed if {
	# external side effect from a clean (cli) source is permitted
	inp := object.union(_base_input, {
		"tool_name": "send_email",
		"capability": "send_email",
		"taint": false,
		"side_effect_type": "external",
	})
	result := safe_mcp_proxy.decision with input as inp
	result.decision == "ALLOW"
	result.rule == "default_allow"
}
