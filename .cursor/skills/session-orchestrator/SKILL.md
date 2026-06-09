---
name: session-orchestrator
description: Bind or create a workspace session, then execute the user's task.
---

# Session orchestrator

Triggers: `start work`, `/start-work`, `new task`

1. `./scripts/repos-status.sh` — if `no_repos_yaml` / `empty_registry` and user wants **product** work: **ask** for repos (bootstrap-hub skill). If `self_hosted: true`, register the hub repo at `repos/<alias>` (reference clone) and use worktrees — never hub-root product paths
2. `./scripts/resolve-session.sh` — if unbound, `./scripts/prompt-session-start.sh` → **wait for user** → `bind-session.sh` or `new-session.sh` + bind
3. **Scope before edits** — when the user's message is actionable, infer a short **title**, 1–2 line **goal**, and optional **next** from their intent, then run `./scripts/set-session-scope.sh <codename> --title "…" --goal "…" [--next "…"]` **before** product edits. Do not wait for the user to ask. On task change or pause, update scope again.
4. When `ready`: `./scripts/clone-repos.sh` (refresh) + `./scripts/ensure-worktrees.sh <codename>` when `session.json` has tasks with `repo`
5. Update `TASKS.md` + `session.json` tasks — each task needs `"repo": "<alias>"` from `repos.yaml`
6. Implement in `sessions/<codename>/worktrees/<repo>/` — not `repos/`; hub-root blocked when bound ([docs/REPOS.md](../../../docs/REPOS.md) Guards)
7. Hub layer refresh: **hub-upgrade** skill — `./scripts/hub-upgrade.sh` only
8. `./scripts/sync-session.sh <codename>` after other metadata changes (not needed for scope-only updates — `set-session-scope.sh` syncs index and context)

**New session with known intent:**

```bash
./scripts/new-session.sh "" "Short title from user task"
./scripts/bind-session.sh <codename>
./scripts/set-session-scope.sh <codename> --goal "One or two lines describing the work"
```
