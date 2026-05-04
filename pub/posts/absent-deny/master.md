# ABSENT vs DENY: Two Failure Modes That Look the Same but Aren't

There are two ways a tool invocation can fail to execute in safe-mcp-proxy. They look
similar from the outside — neither produces a result — but they represent fundamentally
different security properties.

Understanding the difference is not academic. It determines whether your agent can be
manipulated into even *trying* to do something dangerous.

---

## What ABSENT means

**ABSENT** means the tool does not exist in this world.

When an agent requests a tool that isn't in the world manifest's `allowed_tools`, the
response is:

```json
{"decision": "ABSENT", "rule": "tool_not_allowlisted", "result": {"error": "Action does not exist in this world"}}
```

The agent received no confirmation that the tool exists. It received no error message
that could be parsed to infer the tool's existence. The tool simply is not part of the
agent's reality.

This is the result of rules 1 and 2 in the policy engine:

1. `tool_name not in allowlist` → **ABSENT / tool_not_allowlisted**
2. `capability_map[capability] == False` → **ABSENT / capability_not_allowed**

---

## What DENY means

**DENY** means a visible action was blocked by policy.

When a tool *is* in the agent's world, but the specific invocation violated a runtime
policy, the response is:

```json
{"decision": "DENY", "rule": "tainted_external_side_effect", "result": {"error": "Denied by policy", "reason": "tainted_external_side_effect"}}
```

The tool exists. The agent can see it. This particular call was rejected because the
request came from an untrusted channel (taint) or the tool's schema was mutated at
runtime (descriptor drift). The tool remains in the agent's world for future calls.

This is the result of rules 3 and 4:

3. `descriptor_hash_valid == False` → **DENY / descriptor_drift**
4. `taint == True AND side_effect_type == "external"` → **DENY / tainted_external_side_effect**

---

## Why the ordering matters

The policy engine evaluates rules in fixed order. ABSENT checks run *before* DENY checks.

This is not arbitrary. A tool not in the allowlist cannot trigger a taint violation —
it cannot be "denied." It does not exist. Evaluating DENY rules first would be
logically incoherent, and operationally dangerous: it could leak information about
tools that should be invisible.

The ordering:

```
1. tool_not_allowlisted?     → ABSENT   (hide)
2. capability_not_allowed?   → ABSENT   (hide)
3. descriptor_drift?         → DENY     (block corrupt schema)
4. tainted + external?       → DENY     (block injection → exfiltration)
5. approval_required?        → ASK      (pause for human)
6. (all clear)               → ALLOW
```

An agent cannot be manipulated into calling something at step 4 if it was stopped at
step 1.

---

## The security implication

Consider a prompt injection attack. The attacker embeds instructions in a web page
that tell the agent: *"Call `dangerous_exec` with this payload."*

**With DENY only:** If `dangerous_exec` is in the registry but blocked at runtime, the
agent knows the tool exists. A sufficiently sophisticated injection might find ways to
work around the block — trying different payloads, different timing, different chains.
The tool is a known target.

**With ABSENT:** `dangerous_exec` is not in `allowed_tools`. The agent has never seen
the tool name. The injection instruction refers to something that does not exist in
the agent's world. The attack has no target.

You cannot be manipulated into calling something you've never seen.

---

## Running the demo

```bash
python -m demos.core.absent_tool_case
```

This invokes `dangerous_exec` with a `cli` source (clean, not tainted). Even though
the source is clean and there is no schema mutation, the tool is absent — it's not in
the allowlist. The result:

```json
{"decision": "ABSENT", "rule": "tool_not_allowlisted", "result": {"error": "Action does not exist in this world"}}
```

Compare to `prompt_injection.py`, which invokes `send_email` from a `web` source.
`send_email` *is* in the allowlist, so it is visible — but the tainted source + external
side effect produces `DENY / tainted_external_side_effect`. The tool exists. The call
was rejected.

Different failure mode. Different security property.

---

## The third outcome: ASK

ABSENT and DENY are terminal. There is a third non-terminal outcome: **ASK**.

ASK is produced by rule 5 when a tool is visible, the invocation is structurally valid,
but the capability is configured with `requires_approval: true` in the manifest. Execution
pauses pending explicit human approval. ASK resolves to ALLOW (approved) or DENY
(rejected) — it is not a failure, it is a checkpoint.

The three outcomes map to three distinct situations:

| Outcome | Tool visible? | Call blocked? | Reason |
|---------|-------------|---------------|--------|
| ABSENT  | No          | N/A           | Tool not in this world |
| DENY    | Yes         | Yes           | Runtime policy violation |
| ASK     | Yes         | Paused        | Human approval required |

---

## See also

- [Repository](https://github.com/sv-pro/safe-mcp-proxy)
- `safe_mcp_proxy/policy_engine.py` — the 6-path decision logic
- `demos/core/absent_tool_case.py` — ABSENT demo
- `demos/core/prompt_injection.py` — DENY demo
- `wiki/absent-deny.md` — concept page
