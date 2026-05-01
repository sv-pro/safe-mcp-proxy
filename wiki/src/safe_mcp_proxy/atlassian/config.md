# `atlassian/config.py`

## Role

`AtlassianProxyConfig` — runtime configuration for the Atlassian MCP passthrough. Can be constructed directly or loaded from environment variables via `from_env()`.

## Key symbols

| Name | Kind | Description |
|------|------|-------------|
| `AtlassianProxyConfig` | dataclass | All runtime config for `MCPPassthrough` |
| `AtlassianProxyConfig.from_env` | classmethod | Reads all fields from environment variables |
| `AtlassianProxyConfig.is_proxy_mode` | property | `True` when `mode == "proxy"` |
| `AtlassianProxyConfig.capability_filter` | method | Returns a `CapabilityFilter(allowed_tools, denied_tools)` |

## Fields

| Field | Type | Default | Env var |
|-------|------|---------|---------|
| `upstream_url` | str | `""` | `ATLASSIAN_MCP_URL` |
| `mode` | str | `"proxy"` | `ATLASSIAN_PROXY_MODE` |
| `timeout` | int | `30` | `ATLASSIAN_MCP_TIMEOUT` |
| `allowed_tools` | Set[str] | `set()` | `ATLASSIAN_ALLOWED_TOOLS` (comma-separated) |
| `denied_tools` | Set[str] | `set()` | `ATLASSIAN_DENIED_TOOLS` (comma-separated) |
| `manifest_path` | Optional[Path] | `None` | `ATLASSIAN_MANIFEST_PATH` |
| `source_channel` | str | `"cli"` | `ATLASSIAN_SOURCE_CHANNEL` |
| `debug` | bool | `False` | `ATLASSIAN_DEBUG` (`1`/`true`/`yes`) |

## Modes

- `mode="proxy"` — requests are forwarded through the safe-mcp-proxy pipeline.
- `mode="direct"` — proxy is bypassed; clients connect to Atlassian MCP directly (config struct still used for filter).

## Depends on

- [[src/safe_mcp_proxy/atlassian/filter]] — `CapabilityFilter`

## Used by

- [[src/safe_mcp_proxy/atlassian/passthrough]] — `MCPPassthrough` receives one at construction
- `api/main.py` — builds config from env when setting up `POST /atlassian/mcp`

## See also

- [[src/safe_mcp_proxy/atlassian/index]] — subpackage overview
