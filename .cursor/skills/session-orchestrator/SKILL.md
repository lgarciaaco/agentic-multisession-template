---
name: session-orchestrator
description: Bind or create a workspace session, then execute the user's task.
---

# Session orchestrator

Triggers: `start work`, `/start-work`, `new task`

1. Hub root = `WORKSPACE_ROOT` or directory containing `sessions/_codenames.yaml`
2. `./scripts/resolve-session.sh` — if unbound, `./scripts/prompt-session-start.sh` → **wait for user** → `bind-session.sh` or `new-session.sh` + bind
3. Update `TASKS.md` + `session.json` with goal/tasks
4. Implement in project root + `sessions/<codename>/`
5. `./scripts/sync-session.sh <codename>` after metadata changes
