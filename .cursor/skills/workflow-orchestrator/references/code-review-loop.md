# Code review loop persistence

Autonomous fix loop: **review → INCOMPLETE → fixer (parent) → review** until **PASS**. User gates only at brief and plan.

| File | Writer | Role |
|------|--------|------|
| `reviews/workspace/review-*/` | code-reviewer + agents | transient handoff |
| `reviews/r-NNN.json` | synthesizer | append-only summary |
| `artifacts/code-review-disposition.md` | fixer (parent) | SUGGESTION/NIT accept/refuse + fix log |
| `progress.json` `last_review` | advance script | latest review pointer |
| `workflow.json` `loops.code_review` | advance script | iteration + last_verdict + task_id |
| `workflow.json` `loops.implementation` | mark-ready script | active_task + ready_for_review |

## Enter loop (no user gate)

When implementation slice for task `tN` is complete:

```bash
python3 scripts/workflow-mark-implementation-ready.py <codename> tN
```

Replaces the old "all tasks done" guard — sequential multi-PR plans review per task slice.

Legacy (all tasks done):

```bash
python3 scripts/workflow-begin-code-review.py <codename>
```

## Helper scripts

```bash
python3 scripts/workflow-code-review-enrich-scope.py <codename> sessions/<codename>/reviews/workspace/<review-id>
python3 scripts/workflow-code-review-advance.py <codename> [r-NNN]
```

## Verdict → phase

| Verdict | Phase after advance | Conductor action |
|---------|---------------------|------------------|
| `PASS` | `delivery` | Auto `workflow-write-delivery-report.py` |
| `INCOMPLETE` | `code_review_loop` | Fixer: REQUIRED + dispositions → re-review |
| `FAIL` | `code_review_loop` | Escalate BLOCKER to user |

Open **SUGGESTION/NIT** in merged findings → synthesizer **INCOMPLETE** (disposition sub-loop). **PASS_WITH_NITS** is legacy alias for PASS when findings are empty.

## Intent acceptance

`scope_manifest.workflow.acceptance_criteria` filtered to `loops.code_review.task_id` when set.

## Writable

`sessions/<codename>/reviews/`, `artifacts/code-review-disposition.md`, worktrees during fixer phase. `./scripts/sync-session.sh <codename>`.
