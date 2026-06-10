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
| SUGGESTION | Should fix; author must disposition before APPROVE |
| NIT | Clarity; author must disposition before APPROVE |
| BLOCKER | Never |

## Verdict

| Verdict | When |
|---------|------|
| APPROVE | All criteria met; no REQUIRED; **no open SUGGESTION/NIT in findings**; every disposition row validated (see below) |
| REVISE | Any REQUIRED or `met: false`; or open SUGGESTION/NIT awaiting author disposition; or invalid/missing disposition validation |
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

## Disposition validation (REQUIRED on fail)

When `action-plan.md` has **Reviewer disposition** rows, or prior `findings/plan.json` had SUGGESTION/NIT:

| Check | FAIL when → REQUIRED |
|-------|----------------------|
| Missing row | Prior SUGGESTION/NIT has no matching disposition row |
| Undecided | Row missing **accepted** or **refused** decision |
| Accepted not applied | Decision **accepted** but plan body unchanged for that finding |
| Refused without rationale | Decision **refused** but rationale empty or generic |
| Invalid refusal | **refused** rationale contradicts brief, ignores constraint, or defers without task/out-of-scope cite |

On validation pass:

- **Do not** re-emit SUGGESTION/NIT for rows you validated — drop them from `findings[]`.
- **refused** rows validated → omit from findings; they remain in the plan table for the user gate only.
- **accepted** rows validated → omit from findings; change must be visible in plan.

First pass (no disposition table, or new SUGGESTION/NIT): emit SUGGESTION/NIT in `findings[]`; verdict **REVISE** until author dispositions and you validate.

## Process (REQUIRED on fail)

Reviewer edited plan; missing evidence citations; APPROVE with REQUIRED present; APPROVE while open SUGGESTION/NIT remain in `findings[]`.

## Evidence format

Cite brief section + SC-n and plan section + task ID.

## Procedure

1. Extract SC-n, constraints, out-of-scope from brief.
2. Read plan sections: Approach, Traceability, Tasks, Test plan, Risks, **Reviewer disposition**.
3. Read `repos.yaml` for aliases.
4. Map SC-n → criteria[] with evidence.
5. DoR on every task row.
6. If disposition table or prior SUGGESTION/NIT: run **Disposition validation**; emit REQUIRED for failures.
7. Else: emit new SUGGESTION/NIT for quality gaps.
8. Write `findings/plan.json` only — empty `findings[]` allowed on APPROVE when only validated **refused** rows remain in the plan.
