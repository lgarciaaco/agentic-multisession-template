# CI fixer rules

**Runner:** parent agent (conductor) in `ci_observe` phase when verdict is `TEST_FAILURE` or `CONFLICT`.

## Purpose

Fix CI failures or merge conflicts so the PR goes green without user intervention.

## On CONFLICT

Detected via `gh pr view <number> --json mergeStateStatus` → `CONFLICTING`. This check runs BEFORE CI polling — `gh pr checks` does not surface merge conflicts.

1. Identify target branch from `repos.yaml` `pr_target_branch` (fallback `default_branch`).
2. Run `git fetch origin <target> && git rebase origin/<target>`.
3. If rebase succeeds: `git push --force-with-lease`.
4. If rebase has conflicts: attempt resolution; if unresolvable, escalate.

## On TEST_FAILURE

1. Read CI output (e.g. `gh run view --log-failed`).
2. Identify failing test(s) and root cause.
3. Fix the code in the worktree — same fixer pattern as code-review (disposition model not needed; just fix).
4. Commit the fix (conventional-commit: `fix(<scope>): resolve CI failure`).
5. Force-push: `git push --force-with-lease`.

## Rules

- Never force-push to the default/main branch
- Never force-push without `--force-with-lease`
- One fix attempt per CI observe iteration — do not loop internally
- If fix is uncertain or affects unrelated code, escalate immediately
- Maximum scope: changes that directly address the test failure or conflict
- Do not refactor or improve unrelated code during a fix pass

## Escalation

When the fix cannot be made confidently:
- Report the failure type, log excerpt, and attempted resolution
- Suggest user action (manual fix, reopen plan, or abandon PR)
