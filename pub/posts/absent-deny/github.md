# ABSENT vs DENY: Two Failure Modes That Look the Same but Aren't

In [safe-mcp-proxy](https://github.com/sv-pro/safe-mcp-proxy), there are two ways an invocation fails to execute. They look similar — neither produces a result — but they carry different security properties.

## ABSENT — the tool does not exist

```json
{"decision": "ABSENT", "rule": "tool_not_allowlisted", "result": {"error": "Action does not exist in this world"}}
```

Produced when `tool_name` is not in `allowed_tools` in `world_manifest.yaml`. The agent never learned the tool exists. A prompt injection directing the agent to call it has no target.

**Policy rules that produce ABSENT (evaluated first):**
1. `tool_name not in allowlist` → `ABSENT / tool_not_allowlisted`
2. `capability_map[capability] == False` → `ABSENT / capability_not_allowed`

## DENY — a visible action was blocked

```json
{"decision": "DENY", "rule": "tainted_external_side_effect", "result": {"error": "Denied by policy"}}
```

Produced when the tool *is* in the world but the call violated policy — tainted source + external side effect, or a drifted schema.

**Policy rules that produce DENY (evaluated after ABSENT):**
3. `descriptor_hash_valid == False` → `DENY / descriptor_drift`
4. `taint == True AND side_effect_type == "external"` → `DENY / tainted_external_side_effect`

## Why ordering matters

ABSENT checks run before DENY checks. A tool not in the allowlist cannot trigger a taint violation. This ordering prevents information leakage and closes exploitation loops.

```
1. tool_not_allowlisted?   → ABSENT
2. capability_not_allowed? → ABSENT
3. descriptor_drift?       → DENY
4. tainted + external?     → DENY
5. approval_required?      → ASK
6. (all clear)             → ALLOW
```

## Run the demos

```bash
# ABSENT: tool not in allowlist — clean source, no mutation, still absent
python -m demos.core.absent_tool_case

# DENY: tool is visible but call is tainted
python -m demos.core.prompt_injection
```

**See also:** [`wiki/absent-deny.md`](../../wiki/absent-deny.md) · [`policy_engine.py`](../../safe_mcp_proxy/policy_engine.py)
