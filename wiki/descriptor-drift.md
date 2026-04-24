# Descriptor Drift

Detects runtime mutation of tool schemas via SHA256 hashing. A mismatch between the stored hash and the current schema triggers DENY.

## What it is

Every `Tool` record stores a `descriptor_hash` — the SHA256 of its schema at registration time. Before each invocation, the executor recomputes the hash of the live schema and compares it to the stored value. If they differ, the tool's descriptor has drifted.

## Why it exists

A supply-chain attack against an MCP server could modify tool schemas after startup — for example, changing a `read_file` tool's description to include prompt injection instructions, or altering parameter types to smuggle data. By pinning the hash at startup and verifying it on every call, the proxy detects any such mutation deterministically.

## How it works

Three functions in `descriptor.py`:

```python
def normalize_schema(schema: dict) -> str:
    # Deterministic JSON: sorted keys, no extra whitespace
    return json.dumps(schema, sort_keys=True, separators=(",", ":"))

def compute_descriptor_hash(schema: dict) -> str:
    normalized = normalize_schema(schema)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

def descriptor_hash_valid(schema: dict, expected_hash: str) -> bool:
    return compute_descriptor_hash(schema) == expected_hash
```

The `ToolRegistry.with_mock_tools()` factory calls `compute_descriptor_hash(schema)` for each tool at registration time, storing the result in `tool.descriptor_hash`.

On each `executor.execute()` call, `_tool_context()` calls `descriptor_hash_valid(tool.schema, tool.descriptor_hash)`. If False, `policy_engine.decide()` returns `DENY / descriptor_drift`.

## Demo scenario

The `poisoned_descriptor` scenario in [[src/safe_mcp_proxy/scenarios/index]] demonstrates this: a `setup` function mutates `read_file`'s schema by adding an `encoding` property. The next invocation is denied with rule `descriptor_drift`.

## See also

- [[policy-engine]] — rule 3: `descriptor_drift`
- [[absent-deny]] — DENY outcome
- [[src/safe_mcp_proxy/descriptor]] — implementation
- [[src/safe_mcp_proxy/registry]] — where hashes are pinned at startup
- [[src/safe_mcp_proxy/executor]] — where `descriptor_hash_valid()` is called
- [[src/safe_mcp_proxy/policy_engine]] — evaluates `descriptor_hash_valid` flag as rule 3
