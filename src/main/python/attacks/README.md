# Attack Corpus

This directory contains structured adversarial scenarios used by demos, tests,
and API scenario endpoints. It is not a runnable demo folder.

Primary consumer:

```bash
python -m mcpzero.demo
```

Files:

| File | Purpose |
|---|---|
| `schema.yaml` | Canonical scenario field definitions. |
| `example.yaml` | Minimal scenario used by tests. |
| `email_injection.yaml` / `email_injection.md` | Prompt-injection scenario and source document. |
| `tool_chain.yaml` / `tool_chain.md` | Multi-step tool-chain escalation scenario and narrative. |
| `mcp_poison.json` | Descriptor poisoning scenario. |
| `loader.py` | Scenario parser and validator. |
