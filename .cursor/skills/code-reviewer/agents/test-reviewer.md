# Agent: test reviewer

**Spawn:** Task parallel when scope is changeset or task. **Output:** `findings/tests.json`

## Load

- [rules/universal.md](../rules/universal.md) (tests section)
- [rules/agents/test-reviewer.md](../rules/agents/test-reviewer.md)

## Task prompt template

```text
Test review agent.

Workspace: <workspace_path>
Read scope_manifest.json. Compare code delta to test file changes.
Load rules/agents/test-reviewer.md and universal tests section.

Write <workspace_path>/findings/tests.json.
Return: file path + counts.
```
