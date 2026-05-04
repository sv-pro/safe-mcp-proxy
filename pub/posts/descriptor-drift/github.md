# Descriptor Drift: Detecting Runtime Schema Mutation with a SHA256

A supply-chain attacker modifies a tool's schema after startup. The tool still passes allowlist checks. But the hash doesn't match — and the invocation is denied.

## How it works

At registration, each tool stores a `descriptor_hash`:

```python
tool.descriptor_hash = compute_descriptor_hash(tool.schema)
# = sha256(json.dumps(schema, sort_keys=True, separators=(",", ":")))
```

On every `execute()` call, `descriptor_hash_valid(live_schema, stored_hash)` is checked. If the schema was mutated between startup and invocation:

```json
{"decision": "DENY", "rule": "descriptor_drift"}
```

## Why JSON normalization

`sort_keys=True` ensures the same schema always produces the same hash regardless of insertion order. Canonical JSON is a precondition for deterministic hashing.

## Demo

```bash
python -m demos.core.poisoned_descriptor
# Mutates read_file schema, then invokes → DENY / descriptor_drift
```

The hash appears in every audit entry (`descriptor_hash` field) — you can verify which schema was active at any past decision and detect drift between entries.

**See also:** [`wiki/descriptor-drift.md`](../../wiki/descriptor-drift.md) · [`descriptor.py`](../../safe_mcp_proxy/descriptor.py) · [`attacks/tool_chain.yaml`](../../attacks/tool_chain.yaml)
