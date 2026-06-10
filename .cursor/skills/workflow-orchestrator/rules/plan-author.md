# Plan author rules

**Runner:** Task subagent only (conductor spawns).  
**Input:** frozen `artifacts/problem-brief.md`; REVISE: `findings/plan.json` + optional `artifacts/plan-feedback.md`.  
**Output:** `sessions/<codename>/artifacts/action-plan.md`  
**Read-only:** brief, `repos.yaml`, `docs/PROJECT.md` if present, prior findings.

## Purpose

Convert accepted brief into one traceable, executable action plan.

## Procedure

1. Read `problem-brief.md` — immutable scope.
2. Read `repos.yaml` — only registered aliases.
3. REVISE: read `findings/plan.json` — fix every **REQUIRED** finding in the plan body or **Revision notes**.
4. REVISE: for each **SUGGESTION** and **NIT**, decide **accepted** (apply to plan) or **refused** (defer with rationale). Record every item in **Reviewer disposition** — none left undecided.
5. If `artifacts/plan-feedback.md` exists, incorporate user notes at plan gate.
6. Write `action-plan.md` per template.
7. Do not edit worktrees, `session.json`, or brief.

## Template

```markdown
# Action plan — <title>

**Status:** draft | reviewer_approved | user_approved
**Based on:** problem-brief.md @ accepted
**Version:** <n>

## Approach
Strategy respecting brief constraints and out-of-scope.

## Traceability
| Brief | Plan tasks |
|-------|------------|
| SC-1 | t1, t2 |

## Tasks
| ID | Repo | Summary | Acceptance | Depends |
|----|------|---------|------------|---------|
| t1 | <alias> | … | Testable done condition (no pipe chars) | — |

## Files / areas
Indicative touch points.

## Test plan
Concrete commands; hub + `scripts/`: `python3 scripts/test_*.py`.

## Risks
| Risk | Mitigation |
|------|------------|

## Reviewer disposition

Present when plan loop reached APPROVE after at least one REVISE, or when open SUGGESTION/NIT remain from latest `pr-NNN`.

| Finding (summary) | Severity | Decision | Rationale |
|-------------------|----------|----------|-----------|
| … | SUGGESTION / NIT | accepted / refused | Why applied or deferred |

- **accepted** — change reflected in plan (Tasks, Test plan, Files/areas, or Revision notes)
- **refused** — explicit defer reason (scope, brief constraint, later task id)

## Revision notes

On REVISE only: bullets per REQUIRED finding id or issue; increment **Version** in header.
```

## Task rules

| Rule | Requirement |
|------|-------------|
| Sizing | 1–4h; one deliverable per task |
| IDs | Stable `t1`, `t2`, … |
| Repo | Matches `repos.yaml` alias |
| Acceptance | Observable pass/fail; no "works"/"improve" alone; **no `\|` in cells** (breaks `workflow-accept-plan.sh` sync) |
| Depends | Explicit; no cycles |
| Traceability | Every SC-n ↔ ≥1 task |
| Status | All `pending` on output |
| Disposition | Every SUGGESTION/NIT from prior review → accepted or refused with rationale |

## Hub (`mode: hub`)

When plan touches `scripts/`, `.cursor/`, or hub docs: test plan includes at minimum `python3 scripts/test_session_binding.py`; script changes add git_remotes + hub_upgrade tests per hub-contributing.

## Forbidden

Scope beyond brief; rewrite brief; worktree/code edits; empty test plan; mega-tasks.

## REVISE

Increment **Version**; **Revision notes** for each REQUIRED; **Reviewer disposition** for every SUGGESTION/NIT (accepted or refused + rationale); preserve task IDs when possible.
