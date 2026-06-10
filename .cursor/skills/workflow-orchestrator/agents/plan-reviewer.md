# Agent: plan reviewer

**Spawn:** Task (conductor, plan_loop). **Output:** `findings/plan.json`

The conductor must **not** write findings or set verdict inline. See [rules/conductor.md](../rules/conductor.md) **Subagent isolation**.

## Load

- [rules/plan-reviewer.md](../rules/plan-reviewer.md)
- [rules/agents/plan-reviewer.md](../rules/agents/plan-reviewer.md)
- [references/findings-schema.md](../references/findings-schema.md)

## Task prompt template

```text
Plan review agent.

Workspace: <workspace_path>
Read plan_scope_manifest.json.

Load .cursor/skills/workflow-orchestrator/rules/plan-reviewer.md,
rules/agents/plan-reviewer.md, and references/findings-schema.md.

Read problem-brief.md and action-plan.md from manifest paths.
Read repos.yaml when plan tasks reference repo aliases.

Map each brief success criterion (SC-n) to criteria[] MET|NOT MET with evidence.
Apply Definition-of-Ready checks on every task.
Emit REQUIRED/SUGGESTION/NIT only — never BLOCKER.
Set verdict: APPROVE | REVISE | REJECT.

Write <workspace_path>/findings/plan.json only. Never edit action-plan.md.

Return: verdict, criteria summary (met/total), counts by severity.
```
