# `trace_store.py`

## Role

Read-only streaming filter over the audit JSONL log. Provides a typed `TraceRecord` interface and query methods.

## Key symbols

| Name | Kind | Description |
|------|------|-------------|
| `SCHEMA_VERSION` | constant | `1` — current trace record schema version |
| `TraceRecord` | frozen dataclass | Typed representation of one audit log entry |
| `TraceRecord.from_raw` | staticmethod | Parses a raw dict (from JSON line) into `TraceRecord` |
| `TraceRecord.as_dict` | method | Serializes back to a plain dict (for API responses) |
| `TraceStore` | class | Read-only streaming view of `audit.jsonl` |
| `TraceStore.all` | method | Returns all records |
| `TraceStore.last` | method | Returns last `n` records |
| `TraceStore.filter` | method | Filters by `decision`, `tool`, `since`, `until` |

## `TraceRecord` fields

| Field | Type | Source audit field |
|-------|------|--------------------|
| `id` | `int` | Line number in JSONL |
| `schema_version` | `int` | Always `SCHEMA_VERSION` |
| `timestamp` | `str` | `timestamp` |
| `tool_requested` | `str` | `tool` |
| `decision` | `Decision \| str` | `decision` |
| `rule_hit` | `str` | `rule` |
| `source_channel` | `str` | `source_channel` |
| `taint` | `bool` | `taint` |
| `descriptor_hash` | `str` | `descriptor_hash` |
| `input` | `dict \| None` | `input` (optional) |

## Streaming behavior

`_iter_records()` reads the file line by line, skipping blank lines and malformed JSON. The file is never loaded entirely into memory.

## Depends on

- [[src/safe_mcp_proxy/decision]] — `Decision.parse()`

## Used by

- [[src/api/index]] — `app.state.trace_store` for `/traces` and `/replay/{id}` endpoints

## See also

- [[audit-replay]] — audit log format and replay semantics
- [[absent-deny]] — `TraceStore.filter(decision=...)` filters by ABSENT/DENY/ALLOW
- [[architecture]] — TraceStore reads the audit log that is the pipeline's output
