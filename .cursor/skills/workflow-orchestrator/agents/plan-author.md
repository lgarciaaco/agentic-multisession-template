# Plan author (Task spawn)

**Spawn:** Task from conductor in `plan_loop`. **Output:** `artifacts/action-plan.md` per manifest `plan_path`.

Conductor must not write this file. [rules/conductor.md](../rules/conductor.md) **Subagent isolation**.

## Load

1. [rules/plan-author.md](../rules/plan-author.md)
2. [rules/agents/plan-author.md](../rules/agents/plan-author.md)
3. On skill edits: [skill-optimizer](../../skill-optimizer/SKILL.md)

## Task prompt

```text
Plan author Task agent.

Hub root: <hub_root>
Workspace: <workspace_path>
Read plan_scope_manifest.json.

Load .cursor/skills/workflow-orchestrator/rules/plan-author.md
  and rules/agents/plan-author.md.

Read frozen problem-brief.md (brief_path).
Read repos.yaml for valid repo aliases.
If prior_findings: read findings/plan.json.
  REQUIRED: fix every item in plan or Revision notes.
  SUGGESTION/NIT: decide accepted or refused for each; record in ## Reviewer disposition with rationale.
If user_feedback path set: read artifacts/plan-feedback.md.

Write action-plan.md to plan_path. Template in plan-author rules.
Do not edit worktrees, session.json, or brief.
Acceptance column: no pipe (|) characters.

Return: version, task count, SC-n → task IDs, disposition summary (accepted/refused counts).
```
