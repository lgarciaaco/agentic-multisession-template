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
If prior_findings: read prior findings/plan.json for SUGGESTION/NIT to validate.

Map each SC-n → criteria[] with met + evidence.
DoR on every task. REQUIRED/SUGGESTION/NIT only — never BLOCKER.

Disposition loop:
  First pass: emit SUGGESTION/NIT for quality gaps → REVISE (author dispositions).
  Later pass: validate ## Reviewer disposition rows.
    accepted → verify change in plan; refused → validate rationale.
    Validated rows → omit from findings[].
  APPROVE only when no REQUIRED, all criteria met, findings[] has no SUGGESTION/NIT.
  Validated refusals stay in plan table only — not re-emitted as findings.

Write <workspace>/findings/plan.json only. Never edit action-plan.md.

Return: verdict, criteria met/total, severity counts, disposition rows validated.
```
