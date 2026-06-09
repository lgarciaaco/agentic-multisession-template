# Agent: intent reviewer

**Spawn:** Task parallel when session or user intent. **Output:** `findings/intent.json`

## Load

- [rules/agents/intent-reviewer.md](../rules/agents/intent-reviewer.md)

## Task prompt template

```text
Intent review agent.

Workspace: <workspace_path>
Read scope_manifest.json, sessions/<codename>/TASKS.md, session.json tasks[].acceptance if present.
When scope_manifest.workflow.acceptance_criteria is set (workflow pipeline), use action-plan acceptance
as primary criteria — same task id beats TASKS.md. Else if workflow.json exists, read
sessions/<codename>/artifacts/action-plan.md ## Tasks Acceptance column.
Map each criterion MET|NOT MET. Unmet → REQUIRED.

Write <workspace_path>/findings/intent.json (criteria + findings).
Return: criteria summary + counts.
```
