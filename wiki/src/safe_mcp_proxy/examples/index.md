# `safe_mcp_proxy/examples/`

## Role

Compatibility wrapper package. The runnable demo implementations moved to
`demos/`; modules here delegate to the canonical demo modules so old commands
and imports keep working.

## Wrapper Map

| Wrapper | Canonical module |
|---------|------------------|
| `safe_mcp_proxy.examples.benign_flow` | `demos.core.benign_flow` |
| `safe_mcp_proxy.examples.prompt_injection` | `demos.core.prompt_injection` |
| `safe_mcp_proxy.examples.poisoned_descriptor` | `demos.core.poisoned_descriptor` |
| `safe_mcp_proxy.examples.absent_tool_case` | `demos.core.absent_tool_case` |
| `safe_mcp_proxy.examples.ask_modes` | `demos.core.ask_modes` |
| `safe_mcp_proxy.examples.deterministic_replay` | `demos.core.deterministic_replay` |
| `safe_mcp_proxy.examples.claude_code_demo` | `demos.integrations.claude_code.demo` |
| `safe_mcp_proxy.examples.gemini_demo` | `demos.integrations.gemini.demo` |
| `safe_mcp_proxy.examples.atlassian_demo` | `demos.integrations.atlassian.demo` |
| `safe_mcp_proxy.examples.dashboard_demo` | `demos.product.dashboard.demo` |

## Running

Prefer canonical commands:

```bash
python -m demos.core.benign_flow
python -m demos.core.prompt_injection
python -m demos.core.poisoned_descriptor
python -m demos.core.absent_tool_case
```

Legacy commands still work:

```bash
python -m safe_mcp_proxy.examples.prompt_injection
python -m safe_mcp_proxy.examples.dashboard_demo
```

## Difference from scenarios

These are standalone scripts that print output directly. The [[src/safe_mcp_proxy/scenarios/index]] package provides structured, registered scenarios that are callable from the API and test suite.

## See also

- [[src/safe_mcp_proxy/scenarios/index]] — registered scenario system
- [[src/demos/index]] — canonical demo catalog
- [[absent-deny]] — the two outcomes these demos illustrate
- [[policy-engine]] — each demo exercises a different policy decision path
- [[provenance-taint]] — `prompt_injection.py` demonstrates taint-based DENY
- [[descriptor-drift]] — `poisoned_descriptor.py` demonstrates drift-based DENY
- [[world-manifest]] — demos load `world_manifest.yaml` via `build_executor()`
- [[audit-replay]] — each demo run appends entries to the audit log
- [[architecture]] — demos run the full executor pipeline end-to-end
