# `capability_dsl.py`

## Role

Defines the parameterized capability DSL — typed models and a YAML parser for `capability_definitions` entries in a world manifest. Enables constrained forms over base tools where some arguments are locked at design time and cannot be overridden by the actor at call time.

Ported from `agent-hypervisor/src/agent_hypervisor/authoring/capabilities/`.

## Key symbols

| Name | Kind | Description |
|------|------|-------------|
| `LiteralSource` | dataclass | Fixed value baked into the definition; invisible to the actor |
| `ActorInputSource` | dataclass | Value supplied by the actor at call time |
| `ContextRefSource` | dataclass | Value resolved from a named runtime context key (declared but not yet wired) |
| `ValueSource` | type alias | `Union[LiteralSource, ActorInputSource, ContextRefSource]` |
| `CapabilityArgDef` | dataclass | Binds one argument to a `ValueSource` |
| `CapabilityDef` | dataclass | A constrained form over a `base_tool` with a `name` and `args` mapping |
| `parse_capability_definitions` | function | Parses the `capability_definitions` YAML section into `dict[str, CapabilityDef]` |

## Value sources

| Source | Actor-visible | Overridable | Notes |
|--------|--------------|-------------|-------|
| `LiteralSource(value)` | No — excluded from schema | No — injected after payload stripping | Baked in at manifest compile time |
| `ActorInputSource` | Yes — included in schema | Yes — actor supplies freely | Appears in the scoped tool's JSON Schema |
| `ContextRefSource(ref)` | No | No | Raises `NotImplementedError` in the handler until wired |

## Manifest YAML syntax

```yaml
capability_definitions:
  send_me_email:
    base_tool: send_email
    args:
      to:
        valueFrom:
          literal:
            value: "owner@example.com"
      body:
        valueFrom:
          actor_input: {}
```

`valueFrom` must specify exactly one source kind key. Unknown keys raise `ValueError`.

## How scoped tools are built

[[src/safe_mcp_proxy/registry]] calls `_build_scoped_tool(cap_def, base_tools)` for each `CapabilityDef`:

1. Builds `scoped_schema` containing only `actor_input` args (types inherited from base tool schema)
2. Collects all `literal` arg values into an injection map
3. Returns a synthetic `Tool` whose handler:
   - Strips the actor payload to `actor_input` keys only
   - Merges in literals (literals always win — the actor cannot override them even by injecting the key)
   - Calls the base tool handler with the merged payload

The scoped tool's `capability` equals its own name (e.g., `send_me_email`), enabling independent policy configuration in the manifest's `capabilities` section.

## Depends on

Nothing — pure data types and parsing logic only.

## Used by

- [[src/safe_mcp_proxy/compiler]] — `parse_capability_definitions()` called during manifest compilation
- [[src/safe_mcp_proxy/registry]] — `CapabilityDef` and source types used in `_build_scoped_tool()`

## See also

- [[world-manifest]] — `capability_definitions` YAML section
- [[src/safe_mcp_proxy/registry]] — where scoped tools are built and registered
- [[absent-deny]] — scoped tools go through the same ABSENT/DENY/ALLOW/ASK paths as raw tools
- [[architecture]] — capability_dsl participates in the Registry stage
