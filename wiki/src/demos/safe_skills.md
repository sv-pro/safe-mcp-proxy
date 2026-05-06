# `demos/safe_skills/`

Safe Skills Projection demo. It compares an unsafe agent with direct access to a
skills repository against a protected path where capabilities are projected by
world manifest, workflow, mode, and provenance.

## Files

| File | Purpose |
|------|---------|
| `poisoned_document.md` | Untrusted document containing a hidden instruction to send email |
| `clean_task.md` | Legitimate baseline task |
| `mock_skills_repo/` | Mock `bigquery`, `email`, and `gke` skill definitions |
| `world_manifest.yaml` | Demo world: only `bigquery.read_dataset` is visible in the read-only workflow |
| `run_without_proxy.py` | Naive baseline: discovers and executes all upstream skills |
| `run_with_proxy.py` | Protected path: routes skill execution through projection and guard logic |

## Commands

```bash
python -m demos.safe_skills.run_without_proxy
python -m demos.safe_skills.run_with_proxy
```

Legacy wrappers under `examples/safe_skills_demo/` still work, but new
documentation should point here.

## Expected Protected Result

The hidden instruction attempts `email.send`. The protected runner returns:

```text
DENY / capability_not_allowed
```

The important property is closed-world execution: dangerous skills may exist
upstream, but they are not projected into the agent's current world.

See also:

- [[src/safe_mcp_proxy/capability_projection]]
- [[src/safe_mcp_proxy/skill_registry]]
