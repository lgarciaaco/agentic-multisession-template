# Plan reviewer rules

**Runner:** Task subagent only (conductor spawns).  
**Input:** brief, `action-plan.md`, `plan_scope_manifest.json`.  
**Output:** `<workspace>/findings/plan.json` per [findings-schema.md](../references/findings-schema.md).  
**Read-only:** never edit plan or brief.

## Purpose

Intent-review: map brief SC-n to plan evidence; Definition-of-Ready on tasks. No BLOCKER severity.

## Severity

| Severity | Use |
|----------|-----|
| REQUIRED | Must fix before APPROVE |
| SUGGESTION | Should fix; non-blocking |
| NIT | Clarity |
| BLOCKER | Never |

## Verdict

| Verdict | When |
|---------|------|
| APPROVE | All criteria met; no REQUIRED findings |
| REVISE | Any REQUIRED or `met: false` |
| REJECT | Plan misunderstands brief → `reopen brief` |

## Brief coverage (REQUIRED on fail)

| Check | FAIL when |
|-------|-----------|
| SC coverage | SC-n without task or approach |
| Constraints | Plan violates brief constraints |
| Out-of-scope creep | Task unjustified by brief |
| Traceability | Matrix missing or incomplete |

Populate `criteria[]` per SC-n; `met: false` → REQUIRED finding with evidence.

## Task quality (REQUIRED on fail)

Vague acceptance; mega-task; bad/missing repo alias; broken Depends; missing test plan; hub/scripts touch without `python3 scripts/test_*.py`; acceptance with `\|` breaking sync.

## Process (REQUIRED on fail)

Reviewer edited plan; missing evidence citations; APPROVE with REQUIRED present.

## Evidence format

Cite brief section + SC-n and plan section + task ID.

## Procedure

1. Extract SC-n, constraints, out-of-scope from brief.
2. Read plan sections: Approach, Traceability, Tasks, Test plan, Risks.
3. Read `repos.yaml` for aliases.
4. Map SC-n → criteria[] with evidence.
5. DoR on every task row.
6. Write `findings/plan.json` only.
