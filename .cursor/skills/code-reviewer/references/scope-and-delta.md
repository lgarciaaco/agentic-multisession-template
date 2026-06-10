# Scope and delta

Reviewer derives file set and range — never agent-authored manifests.

## Delta (per worktree, first match)

| # | Range | When |
|---|-------|------|
| 1 | `last_review_sha..HEAD` | latest `reviews/*.json` `head_sha` |
| 2 | `baseline_sha..HEAD` | `checkpoints.json` |
| 3 | `merge-base..HEAD` | `git merge-base <base_branch> HEAD` |
| 4 | `base_branch...HEAD` | three-dot |
| 5 | staged + unstaged | workflow session (`workflow.json` present) or prompt says uncommitted |
| 6 | `full` | empty delta + audit intent |

Record strategy + SHAs in output. `base_branch` from `tasks[].base_branch`, default `main`.

```bash
git merge-base <base_branch> HEAD
git diff --stat <base>..HEAD
git diff --name-only <base>..HEAD
git log --oneline <base>..HEAD
```

## Full prioritization (large trees)

1. Entrypoints 2. auth/security/middleware 3. api/routes/views/handlers 4. config (not secrets) 5. src/lib/app 6. tests

Report files reviewed vs skipped.

## Multi-worktree / ad hoc

- One delta per `tasks[].repo` worktree; task scope uses matching repo only
- No session: path from prompt; `base_branch` from remote default or `main`
- Dirty tree: `changeset` uses commit range unless prompt requests working tree
