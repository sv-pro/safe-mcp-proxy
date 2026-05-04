"""
ZombieAgent Demo — Upstream MCP Test Server

Realistic upstream MCP server for the ZombieAgent taint-tracking demo.
Exposes five tools that map to the demo scenario:

  read_ticket(ticket_id)                — read a support ticket (taint source: external input)
  read_customers()                      — read all customer records (sensitive internal data)
  send_email(to, subject, body)         — send an email (outbound channel, taint sink)
  http_post(url, payload)               — HTTP POST to external URL (outbound channel, taint sink)
  add_ticket_note(ticket_id, note)      — add a note to a ticket (safe internal write)

Run standalone:
    python demos/mcp_test_server.py

Use with safe-mcp-proxy:
    python -m safe_mcp_proxy.mcp_server \\
        --world zombieagent_default \\
        --upstream python demos/mcp_test_server.py

NOTE: run_demo.py uses the Python executor API directly rather than this server.
This file demonstrates what a real upstream would look like and can be used to
test the proxy with actual MCP stdio transport.
"""
import asyncio
import json
from pathlib import Path

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

_DEMOS_DIR = Path(__file__).resolve().parent
_DATA_DIR = _DEMOS_DIR / "data"

_server = Server("zombieagent-upstream")

_TOOLS = [
    types.Tool(
        name="read_ticket",
        description="Read a support ticket by ID. Returns ticket subject and body.",
        inputSchema={
            "type": "object",
            "properties": {"ticket_id": {"type": "string", "description": "Ticket identifier"}},
            "required": ["ticket_id"],
        },
    ),
    types.Tool(
        name="read_customers",
        description="Read all customer records from the CRM. Returns sensitive customer data.",
        inputSchema={"type": "object", "properties": {}},
    ),
    types.Tool(
        name="send_email",
        description="Send an email to a recipient.",
        inputSchema={
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject"},
                "body": {"type": "string", "description": "Email body"},
            },
            "required": ["to", "subject", "body"],
        },
    ),
    types.Tool(
        name="http_post",
        description="Make an HTTP POST request to an external URL.",
        inputSchema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Target URL"},
                "payload": {"type": "string", "description": "Request body (JSON string)"},
            },
            "required": ["url", "payload"],
        },
    ),
    types.Tool(
        name="add_ticket_note",
        description="Add an internal note to a support ticket.",
        inputSchema={
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string", "description": "Ticket identifier"},
                "note": {"type": "string", "description": "Note content"},
            },
            "required": ["ticket_id", "note"],
        },
    ),
]


def _load_tickets() -> dict:
    path = _DATA_DIR / "tickets.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _load_customers() -> list:
    path = _DATA_DIR / "customers.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return []


@_server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return _TOOLS


@_server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.ContentBlock]:
    args = arguments or {}

    if name == "read_ticket":
        tickets = _load_tickets()
        ticket_id = args.get("ticket_id", "")
        ticket = tickets.get(ticket_id)
        if ticket is None:
            result = {"error": f"Ticket {ticket_id!r} not found"}
        else:
            result = {"ticket_id": ticket_id, "subject": ticket["subject"], "body": ticket["body"]}
        return [types.TextContent(type="text", text=json.dumps(result))]

    if name == "read_customers":
        customers = _load_customers()
        result = {"customers": customers, "count": len(customers)}
        return [types.TextContent(type="text", text=json.dumps(result))]

    if name == "send_email":
        result = {
            "ok": True,
            "sent_to": args.get("to"),
            "subject": args.get("subject"),
            "message_id": "msg-upstream-001",
        }
        return [types.TextContent(type="text", text=json.dumps(result))]

    if name == "http_post":
        result = {
            "ok": True,
            "status_code": 200,
            "url": args.get("url"),
            "bytes_sent": len(args.get("payload", "")),
        }
        return [types.TextContent(type="text", text=json.dumps(result))]

    if name == "add_ticket_note":
        result = {
            "ok": True,
            "ticket_id": args.get("ticket_id"),
            "note_id": "note-upstream-001",
            "note": args.get("note"),
        }
        return [types.TextContent(type="text", text=json.dumps(result))]

    raise ValueError(f"Unknown tool: {name!r}")


async def _main() -> None:
    async with stdio_server() as (read, write):
        await _server.run(read, write, _server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(_main())
