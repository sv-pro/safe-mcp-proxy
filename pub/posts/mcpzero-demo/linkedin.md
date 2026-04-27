Claims about security need measurement. MCPZero is the infrastructure that makes "safe-mcp-proxy blocks prompt injection" measurable.

MCPZero runs the same attack corpus against two pipeline architectures: baseline (agent with direct tool access) and protected (agent through the proxy). For each attack, it records what decision each pipeline produced and whether they differ.

The key insight is what the delta shows. It's not just "attacks fail." It's a structured accounting: this attack was denied by tainted_external_side_effect. That one hit descriptor_drift. That one was ABSENT — the tool was never a target because it didn't exist in the world.

Benign operations pass in both pipelines. Attacks produce specific, named denials in the protected pipeline. The specificity is the point: you know why each attack was stopped, not just that it was.

The attack corpus is declared in YAML with expected outcomes. If the protected pipeline produces a different rule than expected, that's a signal — maybe the policy changed, maybe the world manifest was updated.

python -m mcpzero.runner

→ https://github.com/sv-pro/safe-mcp-proxy
