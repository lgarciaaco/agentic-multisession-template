---
name: session-orchestrator
description: Bind or create a workspace session, then execute the user's task.
---

# Session orchestrator

Triggers: `start work`, `/start-work`, `new task`

1. Hub root = `WORKSPACE_ROOT`; ensure `repos.yaml` exists (`cp repos.yaml.example repos.yaml`)
2. `./scripts/resolve-session.sh` — if unbound, `./scripts/prompt-session-start.sh` → **wait for user** → `bind-session.sh` or `new-session.sh` + bind
3. `./scripts/clone-repos.sh` then `./scripts/ensure-worktrees.sh <codename>` when tasks exist
4. Update `TASKS.md` + `session.json` with goal/tasks (`tasks[].repo` = key in `repos.yaml`)
5. Implement in `sessions/<codename>/worktrees/<repo>/` — not `repos/`
6. `./scripts/sync-session.sh <codename>` after metadata changes
