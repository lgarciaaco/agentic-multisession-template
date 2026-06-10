---
name: session-orchestrator
description: Bind or create a workspace session, then execute the user's task.
---

# Session orchestrator

Triggers: `start work`, `/start-work`, `new task`

1. `./scripts/repos-status.sh` — bootstrap if not `ready` ([bootstrap-hub](../bootstrap-hub/SKILL.md))
2. `./scripts/resolve-session.sh` — unbound: `prompt-session-start.sh` → wait → bind or `new-session.sh` + bind
3. **Scope before edits:** `./scripts/set-session-scope.sh <codename> --title "…" --goal "…" [--next "…"]`
4. Tasks need `"repo"` from `repos.yaml` → `./scripts/ensure-worktrees.sh <codename>`
5. Edit `sessions/<codename>/worktrees/<repo>/` only — hub-root blocked when bound ([docs/REPOS.md](../../../docs/REPOS.md))
6. Hub refresh: [hub-upgrade](../hub-upgrade/SKILL.md) → `./scripts/hub-upgrade.sh` only
7. `./scripts/sync-session.sh <codename>` after metadata edits (scope-only: `set-session-scope.sh` syncs)

**New session + known intent:**

```bash
./scripts/new-session.sh "" "Short title"
./scripts/bind-session.sh <codename>
./scripts/set-session-scope.sh <codename> --goal "…"
```

Full delivery pipeline: [workflow-orchestrator](../workflow-orchestrator/SKILL.md) (`/workflow`).
