---
name: session-orchestrator
description: Bind or create a workspace session, then execute the user's task.
---

# Session orchestrator

Triggers: `start work`, `/start-work`, `new task`

1. `./scripts/repos-status.sh` — if `no_repos_yaml` / `empty_registry` and user wants **product** work: **ask** for repos (bootstrap-hub skill); hub-only work can skip
2. `./scripts/resolve-session.sh` — if unbound, `./scripts/prompt-session-start.sh` → **wait for user** → `bind-session.sh` or `new-session.sh` + bind
3. When `ready`: `./scripts/clone-repos.sh` (refresh) + `./scripts/ensure-worktrees.sh <codename>` when `session.json` has tasks with `repo`
4. Update `TASKS.md` + `session.json` — each task needs `"repo": "<alias>"` from `repos.yaml`
5. Implement in `sessions/<codename>/worktrees/<repo>/` — not `repos/`
6. `./scripts/sync-session.sh <codename>` after metadata changes
