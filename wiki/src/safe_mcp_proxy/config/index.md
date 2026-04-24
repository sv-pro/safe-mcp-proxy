# `safe_mcp_proxy/config/`

## Role

Runtime configuration for the proxy: the simulation flag and per-world YAML manifests.

## Files

### `policy.yaml`

Controls whether external side effects are simulated (mocked) or executed for real.

```yaml
simulation:
  external_side_effects: true
```

When `true`, the executor calls `simulate_external_action()` instead of the tool handler for `external` side-effect tools on the ALLOW path. This is the default for tests and demos.

Read by `_load_simulation_flag()` in [[src/safe_mcp_proxy/main]].

### `worlds/`

Named world YAML manifests. Each file follows the same format as `world_manifest.yaml`.

Resolved by `_resolve_manifest_path()` in [[src/safe_mcp_proxy/main]] when `--world <world_id>` is passed. Takes priority over the legacy `worlds/` directory at the repo root.

Built-in worlds:
- `world_a.yaml` — full access (read_file, list_repo, send_email)
- `world_b.yaml` — read-only (read_file only)
- `world_c.yaml` — read_file + list_repo, no send_email

## See also

- [[world-manifest]] — world YAML format
- [[src/safe_mcp_proxy/main]] — loads both files
- [[src/safe_mcp_proxy/simulate]] — `simulate_external_action()`
