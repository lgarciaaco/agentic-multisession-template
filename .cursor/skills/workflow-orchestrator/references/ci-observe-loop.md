# CI observe loop

Auto-enters after PR creation SUCCESS. No user gate.

## Flow

```text
pr_creation SUCCESS → phase: ci_observe
  loop:
    poll CI (gh pr checks)
    classify: GREEN | CONFLICT | TEST_FAILURE | TIMEOUT | FAIL
    GREEN → phase: delivery; break
    CONFLICT → rebase onto pr_target_branch, force-push, re-poll
    TEST_FAILURE → ci-fixer (parent), commit, force-push, re-poll
    TIMEOUT/FAIL → escalate
    workflow-ci-observe-advance.py <codename> <verdict>
    iteration++; cap at 5
```

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/workflow-ci-observe-advance.py` | Advance loop with verdict |

## Lib

`scripts/lib/workflow_ci_observe.py` — `begin_ci_observe()`, `advance_ci_observe()`, `ci_observe_escalate()`, `ci_observe_needs_rebase()`, `ci_observe_needs_fix()`.

## Verdicts

| Verdict | Conductor action | Next |
|---------|-----------------|------|
| `GREEN` | Report success | `delivery` |
| `CONFLICT` | Rebase + force-push | stay `ci_observe` |
| `TEST_FAILURE` | Load `rules/ci-fixer.md`, fix, commit, force-push | stay `ci_observe` |
| `TIMEOUT` | Escalate | stay (user intervention) |
| `FAIL` | Escalate immediately | stay (user intervention) |

## CI fixer

Parent agent (not Task subagent). Rules: `rules/ci-fixer.md`.

- Read failure logs via `gh run view --log-failed`
- Fix in worktree, commit, force-push with `--force-with-lease`
- One fix per iteration — re-poll after push
- Never force-push default branch

## Escalation

At max iterations or on FAIL/TIMEOUT:
- Present CI log excerpt, iteration count, PR URL
- Suggest: manual fix + re-push, or reopen plan
