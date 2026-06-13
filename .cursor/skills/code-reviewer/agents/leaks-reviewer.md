# Agent: leaks reviewer

**Spawn:** Task parallel when `triggers.leaks`. **Output:** `findings/leaks.json`

Repo-hygiene pass for committed secrets, keys, personal/org identifiers, PII, and obvious vulnerability hints in the changeset. Distinct from optional **security-reviewer** (`triggers.security`) which covers auth, injection, and access-control design.

## Load

1. [rules/leaks.md](../rules/leaks.md)
2. [rules/agents/leaks-reviewer.md](../rules/agents/leaks-reviewer.md)

## Task prompt template

```text
Leaks review agent (repo hygiene pass).

Workspace: <workspace_path>
Read scope_manifest.json. triggers.leaks must be true.
Load rules/leaks.md and rules/agents/leaks-reviewer.md.

Write <workspace_path>/findings/leaks.json (agent: leaks). BLOCKER allowed.
Return: file path + counts by severity.
```
