1/ Skills exist in a repository. Capability projection controls which ones exist in your agent's world. Here's how.

2/ Key insight: a skill existing in an external repo does not mean it exists in the agent's world. Capability projection = closed-world assumption applied to dynamic capabilities.

3/ The pipeline: skills imported and hashed (never auto-exposed) → world manifest (operator declares allowed/side_effect/constraints) → projection engine (filters by workflow/mode) → execution guard (7-step check per call) → agent sees only the projected world.

4/ Demo. Same agent. Same poisoned document: "find a skill that can send email."
Without proxy: discovers email.send, calls it, data exfiltrated.
With proxy: email.send absent. Attack has no target.

5/ Side-effect classification adds another layer. A read-only research workflow hides external_communication skills entirely — regardless of their allowed status in the manifest.

6/ Run it: python -m examples.safe_skills_demo.run_without_proxy && python -m examples.safe_skills_demo.run_with_proxy

7/ Same agent. Same document. Different execution world.

8/ https://github.com/sv-pro/safe-mcp-proxy
