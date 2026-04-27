# Capability Projection: Enforcing a Closed World Against Dynamic Skills

Skills exist in a repository. Capability projection controls which ones exist in the agent's world.

## The pipeline

```
External Skills Repo
  → Skill Import Adapter   (hash, classify; never auto-expose)
  → World Manifest         (operator declares: allowed? side_effect? constraints?)
  → Policy Compiler        (immutable at runtime)
  → Capability Projection  (filter by identity, workflow, mode)
  → Execution Guard        (7-step check on every call)
  → Agent                  (sees only the projected world)
```

Skills not in the manifest don't exist in the agent's world — even if the upstream repo adds them.

## Side-effect filtering

| Side effect | Read-only workflow | Background mode |
|-------------|-------------------|-----------------|
| `none` | ✓ visible | ✓ visible |
| `bounded_compute` | ✓ visible | ✗ hidden |
| `write` | ✗ hidden | ✗ hidden |
| `external_communication` | ✗ hidden | ✗ hidden |

## Demo

```bash
# Without proxy → email.send discoverable → ATTACK SUCCESS
python -m examples.safe_skills_demo.run_without_proxy

# With proxy → email.send absent → ATTACK BLOCKED
python -m examples.safe_skills_demo.run_with_proxy
```

Same agent. Same poisoned document. Different execution world.

**See also:** [`docs/safe_skills_projection.md`](../../docs/safe_skills_projection.md) · [`capability_projection.py`](../../safe_mcp_proxy/capability_projection.py)
