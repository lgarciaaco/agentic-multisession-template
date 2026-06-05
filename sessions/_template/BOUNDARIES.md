# Session: CODENAME

Bound to codename `CODENAME` via `sessions/bindings/` (see `sessions/context/`).

## Writable

- `sessions/CODENAME/worktrees/**` — product code (git worktrees from `repos.yaml`)
- `sessions/CODENAME/session.json`, `TASKS.md`, `progress.json`
- Cross-session: `sessions/_inbox/` via `./scripts/session-inbox.sh write`

## Read-only

- `repos/**` — reference clones; search and cite only (refresh: `./scripts/clone-repos.sh`)

## Forbidden

- Any edit under `repos/`
- Any path under `sessions/` except `sessions/CODENAME/` and `sessions/_inbox/`
- `sessions/bindings/`, `sessions/context/`

## Hub sessions (`mode`: `hub`)

For hub scripts/docs only: set `"mode": "hub"` in `session.json` and use tasks with `repo` pointing at the hub entry in `repos.yaml` (optional `path: .`).

## On start

1. `./scripts/resolve-session.sh` — must print `CODENAME` for this chat.
2. Read `repos.yaml`, this file, `session.json`, `TASKS.md`, `progress.json`.
3. `./scripts/clone-repos.sh` if reference clones are missing or stale.
4. `./scripts/ensure-worktrees.sh CODENAME` when `tasks` is non-empty.

See [docs/REPOS.md](../../docs/REPOS.md).
