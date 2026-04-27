1/ "safe-mcp-proxy blocks prompt injection" is easy to claim. MCPZero makes it measurable.

2/ MCPZero runs the same attack corpus against two pipelines: baseline (no proxy) and protected (with proxy). Produces a structured verdict diff for each attack.

3/ The delta isn't just pass/fail. It's: this attack → DENY / tainted_external_side_effect. That one → DENY / descriptor_drift. That one → ABSENT / tool_not_allowlisted (the tool was never a target).

4/ Benign operations pass in both pipelines. Attacks produce specific, named denials. The rule attribution is the point — you know why each attack stopped, not just that it did.

5/ Attack corpus is YAML with expected outcomes. If the protected pipeline fires a different rule than expected → signal. Policy might have changed.

6/ python -m mcpzero.runner → baseline vs protected verdict diff, rule distribution, trace comparison.

7/ Same agent. Same attacks. Different execution world. https://github.com/sv-pro/safe-mcp-proxy
