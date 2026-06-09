# Code review loop persistence

| File | Writer | Role |
|------|--------|------|
| `reviews/workspace/review-*/` | code-reviewer orchestrator + agents | transient handoff |
| `reviews/r-NNN.json` | code-reviewer synthesizer | append-only summary |
| `progress.json` `last_review` | advance script + synthesizer | latest review pointer |
| `workflow.json` `loops.code_review` | advance script | iteration + last_verdict |

## Helper scripts

After code-reviewer scope collector writes `scope_manifest.json`:

```bash
python3 scripts/workflow-code-review-enrich-scope.py <codename> sessions/<codename>/reviews/workspace/<review-id>
```

After synthesizer persists `reviews/r-NNN.json`:

```bash
python3 scripts/workflow-code-review-advance.py <codename> [r-NNN]
```

## loops.code_review updates

| Verdict | Phase after advance | Conductor action |
|---------|-------------------|------------------|
| `PASS`, `PASS_WITH_NITS` | `delivery` | Write delivery report (M7) |
| `INCOMPLETE` | `code_review_loop` | Fix per report; re-run if iteration < max |
| `FAIL` | `code_review_loop` | Escalate to user immediately |

`advance_code_review_loop` keeps `phase: code_review_loop` for non-pass verdicts — the conductor must read `loops.code_review.iteration` vs `max` to decide fix-and-retry vs escalate (same pattern as plan loop REVISE).

## Intent acceptance source

`workflow.acceptance_criteria` in `scope_manifest.json` comes from `artifacts/action-plan.md` ## Tasks. Intent reviewer prefers this over `TASKS.md` for the same task id.

## Writable

`sessions/<codename>/reviews/`, `workflow.json`, `progress.json`. Then `./scripts/sync-session.sh <codename>`.
