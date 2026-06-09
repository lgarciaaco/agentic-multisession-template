# Agent: plan author

**Spawn:** Task (conductor, plan_loop). **Output:** `artifacts/action-plan.md`

## Load

- [rules/plan-author.md](../rules/plan-author.md)
- [rules/agents/plan-author.md](../rules/agents/plan-author.md)

## Task prompt template

```text
Plan author agent.

Workspace: <workspace_path>
Read plan_scope_manifest.json in workspace.

Load .cursor/skills/workflow-orchestrator/rules/plan-author.md and rules/agents/plan-author.md.

Read frozen problem-brief.md from brief_path in manifest.
Read repos.yaml from hub root for valid repo aliases.
If prior_findings in manifest: read findings/plan.json and fix every REQUIRED item.
If user_feedback path exists: read artifacts/plan-feedback.md.

Write action-plan.md to plan_path in manifest. Follow template exactly.
Do not edit worktrees, session.json, or the brief.

Return: version, task count, traceability (SC-n → task IDs).
```
