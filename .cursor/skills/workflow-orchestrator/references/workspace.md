# Plan loop workspace

Transient handoff for plan author ↔ plan reviewer. Code review keeps `review-*` ids under the same `reviews/workspace/` tree.

## Path

`sessions/<codename>/reviews/workspace/<workflow-id>/`

`workflow-id`: `wf-YYYYMMDD-HHMMSS` or `wf-YYYYMMDD-HHMMSS-iter<n>` during multi-iteration test runs.

## Layout

```text
<workspace>/
  plan_scope_manifest.json
  findings/
    plan.json
  report.md                 # plan synthesizer output
```

## plan_scope_manifest.json

Written by conductor before spawning Task agents. See [findings-schema.md](findings-schema.md).

## Lifecycle

1. Conductor creates workspace + manifest
2. Task(plan-author) writes `artifacts/action-plan.md` (outside workspace)
3. Task(plan-reviewer) writes `findings/plan.json`
4. Conductor synthesizes → `report.md` + `artifacts/plan-review/pr-NNN.*`
5. On APPROVE: phase → `plan_user_review`; workspace may be pruned (reviewer validated dispositions; `findings[]` has no open SUGGESTION/NIT)
6. On REVISE: next iteration reuses new workspace; pass `prior_findings` in manifest
   - Open SUGGESTION/NIT → author dispositions in plan
   - Reviewer re-runs → validates accept/refuse before APPROVE

## Writable

Conductor and Task agents under `reviews/workspace/wf-*/`. Never product worktrees during plan loop.
