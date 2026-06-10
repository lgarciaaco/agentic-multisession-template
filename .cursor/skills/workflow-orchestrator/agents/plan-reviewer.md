# Plan reviewer (Task spawn)

**Spawn:** Task from conductor in `plan_loop`. **Output:** `<workspace>/findings/plan.json`.

Conductor must not write findings or verdict inline. [rules/conductor.md](../rules/conductor.md) **Subagent isolation**.

## Load

1. [rules/plan-reviewer.md](../rules/plan-reviewer.md)
2. [rules/agents/plan-reviewer.md](../rules/agents/plan-reviewer.md)
3. [references/findings-schema.md](../references/findings-schema.md)

## Task prompt

```text
Plan reviewer Task agent.

Hub root: <hub_root>
Workspace: <workspace_path>
Read plan_scope_manifest.json.

Load .cursor/skills/workflow-orchestrator/rules/plan-reviewer.md,
  rules/agents/plan-reviewer.md,
  references/findings-schema.md.

Read problem-brief.md and action-plan.md from manifest paths.
Read repos.yaml when tasks reference repo aliases.

Map each SC-n → criteria[] with met + evidence.
DoR on every task. REQUIRED/SUGGESTION/NIT only — never BLOCKER.
Verdict: APPROVE | REVISE | REJECT.

Write <workspace>/findings/plan.json only. Never edit action-plan.md.

Return: verdict, criteria met/total, severity counts.
```
