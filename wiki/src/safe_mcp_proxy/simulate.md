# `simulate.py`

## Role

Returns a synthetic response for external-side-effect tools during tests and demos. Prevents real network or I/O calls while preserving the full enforcement pipeline.

## Key symbols

| Name | Kind | Description |
|------|------|-------------|
| `simulate_external_action` | function | Returns `{"simulated": True, "message": "This action would have been executed"}` |

## When it is called

In [[src/safe_mcp_proxy/executor]], when `simulate_external=True` and the policy decision is `ALLOW` and `tool.side_effect_type == "external"`. The `simulate_external` flag is loaded from `safe_mcp_proxy/config/policy.yaml` (`simulation.external_side_effects`).

The simulation path only fires for ALLOW decisions — policy enforcement runs normally first.

## Depends on

Nothing (no imports beyond stdlib typing).

## Used by

- [[src/safe_mcp_proxy/executor]] — `simulate_external_action()` on the ALLOW path
- [[src/safe_mcp_proxy/bundle_replay]] — `simulate_external=False` (replay does not simulate)

## See also

- [[architecture]] — `simulate_external_action()` is the mock branch on the ALLOW execution path
