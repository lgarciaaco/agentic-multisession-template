# Plan author rules

**Runner:** Task subagent (conductor spawns).  
**Input:** frozen `artifacts/problem-brief.md`; on REVISE: `findings/plan.json` + optional `artifacts/plan-feedback.md`.  
**Output:** `sessions/<codename>/artifacts/action-plan.md`  
**Read-only:** brief, repos.yaml, docs/PROJECT.md when present, prior findings.

## Purpose

Convert accepted brief into a traceable, agent-executable action plan. One artifact — not separate design/tasks files.

## Procedure

1. Read `problem-brief.md` — treat as immutable scope.
2. Read `repos.yaml` — only use aliases that exist.
3. On REVISE: address every REQUIRED finding in `findings/plan.json`; do not ignore SUGGESTION if trivial to fix.
4. If `artifacts/plan-feedback.md` exists, incorporate user notes at plan gate.
5. Write `action-plan.md` per template below.
6. Do not edit worktrees, `session.json`, or the brief.

## Template

```markdown
# Action plan — <title>

**Status:** draft | reviewer_approved | user_approved
**Based on:** problem-brief.md @ accepted
**Version:** <n>

## Approach
Short technical strategy; must respect brief constraints and out-of-scope.

## Traceability
| Brief | Plan tasks |
|-------|------------|
| SC-1 | t1, t2 |
| SC-2 | t3 |

## Tasks
| ID | Repo | Summary | Acceptance | Depends |
|----|------|---------|------------|---------|
| t1 | <alias> | … | Testable done condition | — |

## Files / areas
Likely touch points (indicative).

## Test plan
Concrete commands; hub: `python3 scripts/test_*.py` when `scripts/` touched.

## Risks
| Risk | Mitigation |
|------|------------|
```

## Task decomposition

| Rule | Requirement |
|------|-------------|
| Sizing | 1–4h agent-sized; one logical deliverable per task |
| IDs | Stable `t1`, `t2`, … for session.json sync |
| Repo | Every task has `repo` matching `repos.yaml` alias |
| Acceptance | Testable — observable pass/fail; no "works", "clean up", "improve" alone |
| Dependencies | Explicit in Depends column; no circular refs |
| Traceability | Every SC-n maps to ≥1 task; every task maps to ≥1 SC-n |
| Status | All tasks `pending` on output |

## Acceptance wording

- **Good:** "POST /api/orders returns 201 with order id when payload is valid"
- **Good:** "Unit test `test_checkout_expired_token` fails before fix and passes after"
- **Bad:** "Implement checkout"
- **Bad:** "Make it work"

## Hub sessions (`mode: hub`)

When plan touches `scripts/`, `.cursor/`, or hub docs:

- Test plan must include `python3 scripts/test_session_binding.py` at minimum
- Note hub-contributing test trio when scripts change: `test_session_binding.py`, `test_git_remotes.py`, `test_hub_upgrade.py`

## Forbidden

- Expanding scope beyond brief without marking as out-of-scope violation (plan reviewer will REVISE)
- Rewriting brief sections
- Code changes or worktree edits
- Empty test plan for non-trivial scope
- Mega-tasks bundling unrelated work

## On REVISE iteration

- Increment **Version** in plan header
- Add short **Revision notes** subsection listing fixes applied per finding ID
- Preserve task IDs where possible; do not renumber without reason
