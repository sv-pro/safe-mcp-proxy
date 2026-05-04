1/ Prompt injection works because agents treat web content as operator instructions. Here's how taint propagation fixes this at the execution layer.

2/ Every request in safe-mcp-proxy carries a Provenance object. Source channel: cli, email, web, or tool_output. Three of those are tainted by default. cli is the only clean channel.

3/ Taint is monotonic. Once a request chain starts from web or email, it stays tainted — even through intermediate tool outputs. You can't launder tainted data through a clean channel.

4/ The policy rule: tainted + external side effect = DENY. An agent reading a web page (tainted) cannot call send_email (external). The rule fires before the tool handler is called.

5/ Read operations still work. The agent can read files from tainted contexts. Only actions that send data outside the system are blocked when the origin is untrusted.

6/ Run it: python -m demos.core.prompt_injection → DENY / tainted_external_side_effect

7/ The attack corpus at attacks/email_injection.yaml formalizes the scenario. With the proxy: blocked. Without: exfiltrated.

8/ https://github.com/sv-pro/safe-mcp-proxy
