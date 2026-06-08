# Agent: performance reviewer (optional)

**Spawn:** Task parallel when `triggers.performance`. **Output:** `findings/performance.json`

## Load

1. [rules/performance.md](../rules/performance.md)
2. [rules/agents/performance-reviewer.md](../rules/agents/performance-reviewer.md)

## Task prompt template

```text
Performance review agent (deep pass).

Workspace: <workspace_path>
Read scope_manifest.json. triggers.performance must be true.
Load rules/performance.md and rules/agents/performance-reviewer.md.

Write <workspace_path>/findings/performance.json.
Return: file path + counts.
```
