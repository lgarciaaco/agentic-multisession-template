# Agent: security reviewer (optional)

**Spawn:** Task parallel when `triggers.security`. **Output:** `findings/security.json`

Deep pass for auth, injection, IDOR, and access-control design — not committed secrets/PII hygiene (see **leaks-reviewer** when `triggers.leaks` on changeset/task scope).

## Load

1. [rules/security.md](../rules/security.md)
2. [rules/agents/security-reviewer.md](../rules/agents/security-reviewer.md)
3. Language files for langs in scope

## Task prompt template

```text
Security review agent (deep pass).

Workspace: <workspace_path>
Read scope_manifest.json. triggers.security must be true.
Load rules/security.md and rules/agents/security-reviewer.md.

Write <workspace_path>/findings/security.json. BLOCKER allowed.
Return: file path + counts.
```
