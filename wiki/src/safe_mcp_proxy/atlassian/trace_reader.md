# `atlassian/trace_reader.py`

## Role

Read-only interface over the Atlassian-specific JSONL audit log (`safe_mcp_proxy/logs/atlassian_requests.jsonl`). Provides filtering and statistics analogous to the core `TraceStore` but scoped to Atlassian request/decision/response entries.

## Key symbols

| Name | Kind | Description |
|------|------|-------------|
| `TraceEntry` | dataclass | One JSONL line: `direction`, `timestamp`, `trace_id`, `payload`, `tool`, `decision`, `rule`, `tainted`, `flow_labels` |
| `TraceEntry.from_dict` | classmethod | Parses a raw JSONL dict → `TraceEntry` |
| `TraceEntry.as_dict` | method | Serializes back to dict (drops `payload` for compact representation) |
| `AtlassianTraceReader` | class | Read-only log reader; accepts a `log_path: Path` |
| `AtlassianTraceReader.all` | method | Returns all entries; returns `[]` if file does not exist |
| `AtlassianTraceReader.decisions` | method | Filters to `direction == "decision"` entries only |
| `AtlassianTraceReader.by_trace` | method | Returns all entries for a given `trace_id` |
| `AtlassianTraceReader.filter` | method | Filter decisions by `decision`, `tool`, `last N` |
| `AtlassianTraceReader.stats` | method | Returns `{"total": int, "counts": dict}` of decision counts |

## Entry directions

| Direction | Meaning |
|-----------|---------|
| `"request"` | Incoming JSON-RPC request payload |
| `"decision"` | Policy decision (tool, decision, rule, tainted, flow_labels, trace_id) |
| `"response"` | Outgoing JSON-RPC response payload |

## Depends on

Nothing outside the standard library.

## Used by

- [[src/safe_mcp_proxy/atlassian/cli]] — feeds `AtlassianTraceReader` to CLI commands
- `api/main.py` — exposes trace data via `GET /atlassian/traces` (if wired)

## See also

- [[src/safe_mcp_proxy/trace_store]] — analogous core module
- [[audit-replay]] — audit log format and conventions
- [[src/safe_mcp_proxy/atlassian/index]] — subpackage overview
