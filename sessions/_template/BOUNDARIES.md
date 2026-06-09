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
- `sessions/bindings/`, `sessions/context/`, `sessions/index.json`

## Enforced by hooks

Cursor path guards deny edits to `repos/`, `sessions/bindings/`, `sessions/context/`, `sessions/index.json`, and other sessions' directories. Default sessions may edit only `sessions/CODENAME/`. Hub-mode sessions (`mode: hub`) may also edit `scripts/`, `.cursor/`, `docs/`, and these hub root files only: `AGENTS.md`, `SESSIONS.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `CUSTOMIZE.md`, `README.md`, `repos.yaml`, `repos.yaml.example`, `.hub-version`, `.hub-upstream.example`.

## Hub sessions (`mode`: `hub`)

For hub scripts/docs only: set `"mode": "hub"` in `session.json` and use tasks with `repo` pointing at the hub entry in `repos.yaml` (optional `path: .`).

## On start

1. `./scripts/resolve-session.sh` — must print `CODENAME` for this chat.
2. Read `repos.yaml`, this file, `session.json`, `TASKS.md`, `progress.json`.
3. When work intent is clear: `./scripts/set-session-scope.sh CODENAME --title "…" --goal "…"` before product edits.
4. Read `docs/PROJECT.md` if present (project coding guidelines).
5. `./scripts/clone-repos.sh` if reference clones are missing or stale.
6. `./scripts/ensure-worktrees.sh CODENAME` when `tasks` is non-empty.

See [docs/REPOS.md](../../docs/REPOS.md).
