---
name: session-orchestrator
description: Bind or create a workspace session, then execute the user's task.
---

# Session orchestrator

Triggers: `start work`, `/start-work`, `new task`

1. Hub root = `WORKSPACE_ROOT` or directory containing `sessions/_codenames.example.yaml`
2. `./scripts/resolve-session.sh` — if unbound, `./scripts/prompt-session-start.sh` → **wait for user** → `bind-session.sh` or `new-session.sh` + bind
3. `./scripts/ensure-worktrees.sh <codename>` when `session.json` has tasks and hub is a git repo
4. Update `TASKS.md` + `session.json` with goal/tasks
5. Implement in `sessions/<codename>/worktrees/<task-id>/` (product mode); hub root read-only unless `mode: hub`
6. `./scripts/sync-session.sh <codename>` after metadata changes
