Prompt injection attacks work because agents treat data from the web as instructions from their operator. The fix isn't better alignment — it's tracking where data came from and enforcing rules at the execution boundary.

In safe-mcp-proxy, every request carries a Provenance object that records its source channel. Three channels are tainted by default: email, web, and tool_output. The cli is the only clean channel.

Taint is monotonic. A chain of tool calls that starts from a web-sourced input remains tainted for its entire lifetime — even if intermediate steps pass through clean channels. Once tainted, always tainted.

The policy rule is simple: tainted request + external side effect = DENY. An agent that reads a web page (tainted) cannot be directed to call send_email (external). The rule fires at the execution layer, before the tool handler is ever called.

Read operations are not affected. The agent can still read files from tainted contexts. Only actions that send data outside the system are blocked when the origin is untrusted.

Try it: python -m demos.core.prompt_injection → DENY / tainted_external_side_effect

→ https://github.com/sv-pro/safe-mcp-proxy
