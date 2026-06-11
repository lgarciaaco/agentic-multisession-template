# PR creation phase

Auto-enters after code review PASS. No user gate.

## Flow

```text
code_review PASS → phase: pr_creation
  → commit (git-commit skill)
  → push + draft PR (pr-create skill)
  → workflow-advance-pr-creation.py SUCCESS <url>
  → phase: ci_observe
```

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/workflow-advance-pr-creation.py` | Advance loop: SUCCESS, RETRY, or FAIL |

## Lib

`scripts/lib/workflow_pr_creation.py` — `begin_pr_creation()`, `advance_pr_creation()`, `pr_creation_escalate()`.

## Verdicts

| Verdict | Next phase |
|---------|-----------|
| `SUCCESS` | `ci_observe` |
| `RETRY` | stay `pr_creation` (push failed, gh error) |
| `FAIL` | stay `pr_creation`; escalate at max |

## Branch targeting

Read from `repos.yaml`:
1. `pr_target_branch` (explicit per-repo)
2. `default_branch` (fallback)

Access via `scripts/lib/repos.py` → `pr_target_branch(repo_cfg)`.

## PR URL

Stored on active task in `session.json` → `tasks[].pr` after SUCCESS.
