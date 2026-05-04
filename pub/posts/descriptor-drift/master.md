# Descriptor Drift: Detecting Runtime Schema Mutation with a SHA256

Consider a supply-chain attack against an MCP server. An attacker doesn't replace the
tool entirely — that's too obvious. Instead, they modify the schema of `read_file` after
startup. Maybe they change the description to include prompt injection instructions.
Maybe they add a new parameter to smuggle data. The tool is still called `read_file`.
The agent has no reason to distrust it.

Descriptor drift detection closes this attack vector.

---

## What descriptor drift is

Every tool in safe-mcp-proxy stores a `descriptor_hash` — the SHA256 of its JSON schema
at registration time. Before each invocation, the executor recomputes the hash of the
live schema and compares it to the stored value.

If they differ, the schema has changed since startup. The invocation is denied:

```json
{"decision": "DENY", "rule": "descriptor_drift", "result": {"error": "Denied by policy"}}
```

---

## How the hash is computed

Three functions in `descriptor.py`:

```python
def normalize_schema(schema: dict) -> str:
    # Deterministic: sorted keys, no extra whitespace
    return json.dumps(schema, sort_keys=True, separators=(",", ":"))

def compute_descriptor_hash(schema: dict) -> str:
    normalized = normalize_schema(schema)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

def descriptor_hash_valid(schema: dict, expected_hash: str) -> bool:
    return compute_descriptor_hash(schema) == expected_hash
```

The normalization step is critical: JSON dictionaries have no guaranteed key ordering.
Without `sort_keys=True`, two representations of the same schema could produce different
hashes. Normalized JSON is canonical — same schema, same hash, always.

At registration, `compute_descriptor_hash(schema)` is called for each tool and stored
as `tool.descriptor_hash`. On each `execute()` call, `descriptor_hash_valid()` compares
the live schema to the stored hash.

---

## Running the demo

```bash
python -m demos.core.poisoned_descriptor
```

The demo:
1. Retrieves the `read_file` tool from the registry
2. Mutates its schema: `tool.schema["properties"]["encoding"] = {"type": "string"}`
3. Invokes `read_file` — the hash no longer matches

Result:
```json
{"decision": "DENY", "rule": "descriptor_drift"}
```

The mutation was caught, even though:
- The request came from `cli` (not tainted)
- The tool is in the allowlist
- There are no taint-related issues

Descriptor drift is checked at rule 3, before taint checks. A corrupted schema is
denied regardless of where the request came from.

---

## Why this matters for supply-chain security

The attack scenario: a compromised MCP server ships a valid tool at startup, passes
initial allowlist checks, and then modifies tool schemas at runtime to introduce
injection vectors or data exfiltration parameters.

Descriptor drift detection makes this attack category fail at the first call after
mutation. The attacker cannot modify the schema silently — every invocation re-checks.

The hash is logged in every audit entry as `descriptor_hash`. This means:
- You can verify after the fact which schema was active at the time of any decision
- You can detect when a schema changed between two audit entries
- Replay will catch drift: if the schema changed, the replayed hash won't match the recorded one

---

## The attack corpus

`attacks/tool_chain.yaml` formalizes this scenario: a tool schema mutation followed
by an invocation attempt. `attacks/tool_chain.md` narrates the attack chain and its
detection.

---

## See also

- [Repository](https://github.com/sv-pro/safe-mcp-proxy)
- `safe_mcp_proxy/descriptor.py` — implementation
- `demos/core/poisoned_descriptor.py` — demo
- `attacks/tool_chain.yaml` + `attacks/tool_chain.md` — formalized attack scenario
- `wiki/descriptor-drift.md` — concept page
