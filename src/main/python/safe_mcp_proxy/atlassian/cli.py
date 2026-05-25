"""CLI for inspecting Atlassian MCP proxy traces.

Usage:
    python -m safe_mcp_proxy.atlassian.cli [command] [options]

Commands:
    list    List decision entries (default)
    stats   Show decision counts
    trace   Show all entries for a specific trace_id

Options:
    --log PATH       Path to JSONL log (default: safe_mcp_proxy/logs/atlassian_requests.jsonl)
    --decision D     Filter by decision (ALLOW | DENY | ABSENT)
    --tool TOOL      Filter by tool name
    --last N         Show last N decisions
    --trace-id ID    Show all entries for a trace_id (used with trace command)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .trace_reader import AtlassianTraceReader


def _default_log() -> Path:
    return Path(__file__).resolve().parents[2] / "safe_mcp_proxy" / "logs" / "atlassian_requests.jsonl"


def _fmt_decision(d: str) -> str:
    colours = {"ALLOW": "\033[32m", "DENY": "\033[31m", "ABSENT": "\033[33m"}
    reset = "\033[0m"
    return f"{colours.get(d, '')}{d:6}{reset}"


def cmd_list(reader: AtlassianTraceReader, args: argparse.Namespace) -> int:
    entries = reader.filter(
        decision=args.decision,
        tool=args.tool,
        last=args.last,
    )
    if not entries:
        print("No entries found.")
        return 0
    for e in entries:
        labels = f"  labels={e.flow_labels}" if e.flow_labels else ""
        taint = "  tainted" if e.tainted else ""
        print(
            f"[{e.timestamp}]  {_fmt_decision(e.decision or '?')}  "
            f"tool={e.tool}  rule={e.rule}"
            f"{taint}{labels}  trace={e.trace_id[:8]}"
        )
    return 0


def cmd_stats(reader: AtlassianTraceReader, _args: argparse.Namespace) -> int:
    s = reader.stats()
    print(f"Total decisions : {s['total']}")
    for decision, count in sorted(s["counts"].items()):
        print(f"  {_fmt_decision(decision)} : {count}")
    return 0


def cmd_trace(reader: AtlassianTraceReader, args: argparse.Namespace) -> int:
    if not args.trace_id:
        print("Error: --trace-id required for 'trace' command.", file=sys.stderr)
        return 1
    entries = reader.by_trace(args.trace_id)
    if not entries:
        print(f"No entries found for trace_id={args.trace_id!r}")
        return 0
    for e in entries:
        print(json.dumps(e.as_dict(), indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m safe_mcp_proxy.atlassian.cli",
        description="Inspect Atlassian MCP proxy traces.",
    )
    parser.add_argument("command", nargs="?", default="list",
                        choices=["list", "stats", "trace"])
    parser.add_argument("--log", default=None,
                        help="Path to JSONL log file")
    parser.add_argument("--decision", default=None,
                        help="Filter by decision: ALLOW | DENY | ABSENT")
    parser.add_argument("--tool", default=None,
                        help="Filter by tool name")
    parser.add_argument("--last", type=int, default=None,
                        help="Show last N decisions")
    parser.add_argument("--trace-id", dest="trace_id", default=None,
                        help="Trace ID to inspect (for 'trace' command)")

    args = parser.parse_args(argv)
    log_path = Path(args.log) if args.log else _default_log()
    reader = AtlassianTraceReader(log_path)

    dispatch = {"list": cmd_list, "stats": cmd_stats, "trace": cmd_trace}
    return dispatch[args.command](reader, args)


if __name__ == "__main__":
    sys.exit(main())
