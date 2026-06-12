# Child reviewer (Task spawn)

**Spawn:** Task from parent in `/sessions-orchestrator` when checking children. **Model:** `claude-4.6-sonnet-medium-thinking`. **Output:** structured review for one child (parent synthesizes table).

When updating the model slug, also update the **Model assignments** table in [SKILL.md](../SKILL.md).

Parent must not inline multi-child review — spawn one Task per active child. Read-only: never edit child sessions.

## Load

1. Monitor JSON row for this child (`phase`, `pending_gate`, `gate_review`, `resume_hint`, `error`)
2. Parent `artifacts/program-plan.md` — decomposition scope for this codename
3. When `gate_review.artifact_present`: read artifact at `gate_review.artifact_path`
   - `brief_review` → `artifacts/problem-brief.md`
   - `plan_user_review` → `artifacts/action-plan.md`

## Task prompt

```text
Child reviewer Task agent — one child only.

Hub root: <hub_root>
Parent codename: <parent>
Child codename: <child>
Monitor JSON (this child): <paste child snapshot from program-monitor.py>

Read parent sessions/<parent>/artifacts/program-plan.md for this child's decomposition scope.
If gate_review.artifact_present, read sessions/<child>/<artifact> and assess against scope.

Return exactly these sections:

## Status
One line for parent table Status column (phase progress, stuck/unstuck, gate readiness).

## Parent assessment
Mandatory when artifact present OR pending_gate is brief_review / plan_user_review:
- Alignment with decomposition scope (title + goal)
- Gaps or drift from ingest
- Recommended parent action: accept gate, reopen, or inbox correction (do not route — parent user decides)

## Child agent action
What the child /workflow-orchestrator tab should do next (from resume_hint + artifact state).
One short imperative sentence.
```

## Parent synthesis

Merge each subagent return into the mandatory chat format in [SKILL.md](../SKILL.md) **Check children**.
