# `descriptor.py`

## Role

Deterministic SHA256 hashing of tool schemas. Used to detect descriptor drift at invocation time.

## Key symbols

| Name | Kind | Description |
|------|------|-------------|
| `normalize_schema` | function | Produces deterministic JSON string: sorted keys, no extra whitespace |
| `compute_descriptor_hash` | function | Returns SHA256 hex digest of normalized schema |
| `descriptor_hash_valid` | function | Returns `True` if `compute_descriptor_hash(schema) == expected_hash` |

## Implementation

```python
def normalize_schema(schema: dict) -> str:
    return json.dumps(schema, sort_keys=True, separators=(",", ":"))

def compute_descriptor_hash(schema: dict) -> str:
    return hashlib.sha256(normalize_schema(schema).encode("utf-8")).hexdigest()

def descriptor_hash_valid(schema: dict, expected_hash: str) -> bool:
    return compute_descriptor_hash(schema) == expected_hash
```

## Depends on

- `hashlib`, `json` (stdlib only)

## Used by

- [[src/safe_mcp_proxy/registry]] — `compute_descriptor_hash()` called at tool registration
- [[src/safe_mcp_proxy/executor]] — `descriptor_hash_valid()` called in `_tool_context()`; `compute_descriptor_hash()` for the audit log entry

## See also

- [[descriptor-drift]] — concept page explaining the threat model
