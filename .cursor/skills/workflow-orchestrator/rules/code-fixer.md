# Code fixer rules (implementation agent in code review loop)

**Runner:** parent agent (conductor developer) — not a Task subagent.  
**Input:** latest `reviews/r-NNN-report.md`, `artifacts/code-review-disposition.md`, worktree paths from scope.  
**Output:** fixes in `sessions/<codename>/worktrees/**`; updated disposition file.

## Purpose

Autonomous fix loop after code review **INCOMPLETE**. Reviewer is authoritative. Fix every **REQUIRED** and **BLOCKER** (if recoverable without user). Disposition every **SUGGESTION** and **NIT** like plan-author.

## When

Phase `code_review_loop` and advance script printed **INCOMPLETE** (or **FAIL** without escalation). Do **not** ask the user to choose between commit, PR, or review.

## Forbidden (conductor)

| Forbidden | Required instead |
|-----------|------------------|
| Ask user to commit before review | Include uncommitted worktree changes in next review scope |
| Ask "code review or PR when ready?" | Auto-run next review iteration |
| Inline specialist findings | Task subagents per code-reviewer SKILL only |
| Skip disposition for SUGGESTION/NIT | Record every row before re-review |

## Procedure

1. Read latest `reviews/r-NNN-report.md` — fix every **REQUIRED** finding in worktrees (or document why impossible → escalate).
2. For each **SUGGESTION** and **NIT**: decide **accepted** (apply fix) or **refused** (defer with rationale). Record in **Reviewer disposition** table — none undecided.
3. **accepted** — change reflected in worktree; cite file paths in disposition row.
4. **refused** — cite scope/plan constraint, out-of-scope, or defer to later task id.
5. On validation **INCOMPLETE** (reviewer rejected a disposition): update fix or disposition row; keep prior validated rows.
6. Do **not** require git commit between fix and re-review. Conductor re-runs review with working tree included.
7. When all REQUIRED fixed and dispositions recorded → spawn next code review iteration (new `review-*` workspace).

## Reviewer disposition template

See `sessions/_template/artifacts/code-review-disposition.md`. Append rows per review id (`r-NNN`).

## Exit

Loop ends when synthesizer returns **PASS** (no open REQUIRED/SUGGESTION/NIT in findings). Validated **refused** rows remain in disposition file only.

Then conductor runs delivery report — no user gate.

## Escalation

**FAIL** with BLOCKER, or iteration ≥ `loops.code_review.max` still **INCOMPLETE** → present stuck summary; user may narrow scope or `reopen plan`.
