# PR create

Create draft pull requests with ticket integration, fork workflow support, and `repos.yaml` branch targeting.

## Triggers

Use when user says "create pr", "open pr", "make pull request", "submit pr", or "create a pr".

## Procedure

### 1. Remote detection

```bash
git remote -v
git config --get remote.pushDefault
```

Determine workflow:
- **Fork (GitHub):** `remote.pushDefault` is `fork` or `fork` remote exists with user's GitHub URL → push to `fork`
- **Direct push:** no fork remote → push to `origin`

### 2. Branch targeting

Resolve PR base branch:
1. Read `repos.yaml` from hub root — find the repo entry matching the current worktree
2. Use `pr_target_branch` if set, else `default_branch`
3. Never target `main`/`master` unless that's what the config specifies

### 3. Ticket detection

Check sources in order:
1. **Branch name** — parse for `PROJ-123/desc`, `feature/PROJ-123`, `123-desc`
2. **Commit messages** — look for ticket references
3. **Ask user** if no ticket found — skip this step when loaded from workflow `pr_creation` phase (autonomous: proceed without ticket or use "n/a")

### 4. Preflight

**Fork workflow (GitHub):**
- Remote `fork` must exist and URL must contain the configured `github_fork_user`
- `remote.pushDefault` must be `fork`
- Never push feature branches to `origin` on fork-configured repos

If `fork` is missing, from hub root:
```bash
./scripts/configure-git-remotes.sh <repo-alias>
./scripts/ensure-worktrees.sh <codename>
```

**Direct push:** verify `origin` is correct; push to `origin`.

### 5. Generate PR content

Use `templates/generic.md` — fill summary, test plan, and ticket reference.

### 6. Create draft PR

**Fork workflow:**
```bash
git push -u fork HEAD
gh pr create --draft \
  --title "[TICKET] Title" \
  --body "$(cat <<'EOF'
<template content>
EOF
)" \
  --head <fork_user>:<branch> \
  --base <pr_target_branch>
```

**Direct push:**
```bash
git push -u origin HEAD
gh pr create --draft \
  --title "[TICKET] Title" \
  --body "$(cat <<'EOF'
<template content>
EOF
)" \
  --base <pr_target_branch>
```

### 7. Report

Tell user:
- PR created as draft
- How to mark ready: `gh pr ready <number>`
- PR URL
- Confirm push remote (fork vs origin)

## Rules

- Always create as draft (`--draft`)
- Ticket in title when available: `[TICKET] Description`
- Fork repos: push to `fork` only — never `origin` for feature branches
- Fork PR head: always `--head <fork_user>:<branch>`
- No origin fallback: if `fork` missing on fork-configured repo, fix remotes first
- Direct-push repos: push and PR via `origin`
- Base branch from `repos.yaml` `pr_target_branch` (fallback `default_branch`)
