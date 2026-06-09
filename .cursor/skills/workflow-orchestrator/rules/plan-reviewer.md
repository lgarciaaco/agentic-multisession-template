# Plan reviewer rules

**Runner:** Task subagent (conductor spawns).  
**Input:** `artifacts/problem-brief.md`, `artifacts/action-plan.md`, `plan_scope_manifest.json`.  
**Output:** `<workspace>/findings/plan.json` per [findings-schema.md](../references/findings-schema.md).  
**Read-only:** never edit `action-plan.md` or brief.

## Purpose

Intent-review for plans — map brief success criteria to plan evidence; apply Definition-of-Ready checks on tasks. Same rigor as code-reviewer; no BLOCKER severity.

## Severity

| Severity | Use |
|----------|-----|
| REQUIRED | Must fix before APPROVE |
| SUGGESTION | Should fix; does not block APPROVE |
| NIT | Clarity polish |
| BLOCKER | **Never** — no code under review |

## Verdict

| Verdict | When |
|---------|------|
| APPROVE | All criteria MET; no REQUIRED findings |
| REVISE | Any REQUIRED finding or `met: false` (brief still valid) |
| REJECT | Plan misunderstands brief fundamentals — escalate `reopen brief` |

## Completeness vs brief

| Check | Severity | FAIL when |
|-------|----------|-----------|
| Success criterion coverage | REQUIRED | Any SC-n has no plan task or approach coverage |
| Constraint respect | REQUIRED | Plan violates brief Constraints or Out of scope |
| Out-of-scope creep | REQUIRED | Plan task not justified by brief |
| Traceability matrix | REQUIRED | Traceability table missing or SC-n without task mapping |

Populate `criteria[]` — one entry per SC-n from brief. `met: false` → add REQUIRED finding with evidence requirement.

## Task quality (Definition of Ready)

| Check | Severity | FAIL when |
|-------|----------|-----------|
| Acceptance testability | REQUIRED | Vague acceptance ("works", "clean up", "improve", "done") |
| Task sizing | REQUIRED | Task bundles unrelated deliverables |
| Repo mapping | REQUIRED | Missing `repo` or alias not in `repos.yaml` |
| Dependency order | REQUIRED | Implied order but Depends missing, wrong, or circular |
| ID stability | SUGGESTION | Non-stable IDs (not `t1`, `t2`, …) |

## Test and verification

| Check | Severity | FAIL when |
|-------|----------|-----------|
| Test plan present | REQUIRED | Non-trivial plan with no Test plan section |
| Test ↔ acceptance | REQUIRED | Task acceptance has no verification path in Test plan |
| Hub test commands | REQUIRED | `mode: hub` or `scripts/` in Files/areas but no `python3 scripts/test_*.py` |

Hub test rule: fire when `plan_scope_manifest.session_mode == "hub"` **or** plan Files/areas mentions `scripts/`.

## Clarity and feasibility

| Check | Severity | FAIL when |
|-------|----------|-----------|
| Approach coherence | REQUIRED | Approach contradicts brief constraints |
| Ambiguity | REQUIRED | Multiple interpretations of "done" for same task |
| Risk awareness | SUGGESTION | Non-trivial plan with empty Risks table |

Non-trivial: >2 tasks or any task touching security/auth/guards.

## Process

| Check | Severity | FAIL when |
|-------|----------|-----------|
| Read-only | REQUIRED | Reviewer edits plan (process violation — conductor issue) |
| Evidence | REQUIRED | Any `met: false` or REQUIRED finding without brief + plan citation |
| Verdict consistency | REQUIRED | REQUIRED present but verdict APPROVE |

## Evidence format

Each finding and unmet criterion must cite:

- Brief: section + SC-n or constraint text
- Plan: section + task ID or line reference

Example: `SC-2 not met — brief requires expired-token error UI; plan has no task covering SC-2`

## Procedure

1. Read brief — extract SC-1…SC-n, Constraints, Out of scope.
2. Read plan — Approach, Traceability, Tasks, Test plan, Risks.
3. Read `repos.yaml` when repo aliases referenced.
4. Map each SC-n → MET | NOT MET with evidence.
5. Run task-quality and test checks on every task row.
6. Emit findings; set `verdict` per rules above.
7. Write `findings/plan.json` only.
