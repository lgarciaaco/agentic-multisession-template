# Child reviewer (Task spawn)

**Spawn:** Task from parent in `/sessions-orchestrator` when checking children or `/sessions-orchestrator status`. **Model:** `claude-4.6-sonnet-medium-thinking`. **Output:** structured review for one child (parent synthesizes slim chat table + program-status.md detail).

When updating the model slug, also update the **Model assignments** table in [SKILL.md](../SKILL.md).

Parent must not inline multi-child review — spawn one Task per active child. Read-only: never edit child sessions.

## Load

1. Monitor JSON row for this child (`phase`, `pending_gate`, `gate_review`, `resume_hint`, `error`)
2. Parent `artifacts/program-plan.md` — full program decomposition (all sibling goals)
3. `gate_review.sibling_program_context` — read-only sibling scope from monitor (do not read sibling session folders)
4. When `gate_review.artifact_present`: read artifact at `gate_review.artifact_path`
   - `brief_review` → `artifacts/problem-brief.md`
   - `plan_user_review` → `artifacts/action-plan.md`

## Task prompt

```text
Child reviewer Task agent — one child only.

Hub root: <hub_root>
Parent codename: <parent>
Child codename: <child>
Monitor JSON (this child): <paste child snapshot from program-monitor.py>

Read parent sessions/<parent>/artifacts/program-plan.md for ALL sibling goals (cross-child overlap check).
Read gate_review.sibling_program_context from monitor JSON — do not open sibling session folders.
If gate_review.artifact_present, read sessions/<child>/<artifact> and assess against decomposition scope.

Return exactly these sections (order matters):

## Next
One short imperative line for parent chat table slim columns (Child, Phase, Gate, Next). No pipes.

## Parent assessment
Mandatory when artifact present OR pending_gate is brief_review / plan_user_review:
- Alignment with decomposition scope (title + goal)
- Gaps or drift from ingest
- Recommended parent action: accept gate, reopen, or free-text correction via `python3 scripts/program-route-feedback.py <parent> <child> --message "…"` (do not route — parent user decides)

## Cross-child check
Mandatory when sibling_program_context is non-empty OR pending_gate is brief_review / plan_user_review:
- Compare this child's brief/plan to each sibling's stated goal (and plan_summary at plan gate)
- Flag overlap, duplicate work, shared file touchpoints, or conflicting approaches
- Cite sibling codenames explicitly

## Child agent action
What the child /workflow-orchestrator tab should do next (from resume_hint + artifact state).
One short imperative sentence.
```

**Chat vs status:** Parent chat shows **Next** only in the slim table. **Parent assessment**, **Cross-child check**, and **Child agent action** are merged into `artifacts/program-status.md` — not repeated as **Your action** blocks in chat.

## Parent synthesis

Merge each subagent return per [SKILL.md](../SKILL.md) **Check children**: slim chat table from **Next** lines; run `./scripts/program-status-report.sh <parent> --reviews-json <path>` with JSON keyed by child codename:

```json
{
  "child-1": {
    "next": "…",
    "parent_assessment": "…",
    "cross_child_check": "…",
    "child_agent_action": "…"
  }
}
```
