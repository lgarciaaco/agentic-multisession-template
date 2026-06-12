# Agent: infra YAML reviewer (optional)

**Spawn:** Task parallel when `triggers.infra`. **Output:** `findings/infra-yaml.json`

Covers Ansible playbooks/roles, GitHub Actions workflows, and deploy shell scripts — idempotency, trigger semantics, and post-deploy verification.

## Load

1. [rules/infra-yaml.md](../rules/infra-yaml.md)
2. [rules/agents/infra-yaml-reviewer.md](../rules/agents/infra-yaml-reviewer.md)

## Task prompt template

```text
Infra YAML review agent (deep pass).

Workspace: <workspace_path>
Read scope_manifest.json. triggers.infra must be true.
Load rules/infra-yaml.md and rules/agents/infra-yaml-reviewer.md.

Write <workspace_path>/findings/infra-yaml.json (agent: infra-yaml). BLOCKER allowed.
Return: file path + counts by severity.
```
