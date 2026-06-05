# Session: CODENAME

Bound to codename `CODENAME` via `sessions/bindings/` (see `sessions/context/`).

## Writable

- `sessions/CODENAME/worktrees/**` — product code (monorepo checkout on `feature_branch`)
- `sessions/CODENAME/session.json`, `TASKS.md`, `progress.json`
- Cross-session: `sessions/_inbox/` via `./scripts/session-inbox.sh write`

## Read-only

- Hub root (this checkout) — `scripts/`, `.cursor/`, docs at repo root when `mode` is `product`

## Forbidden

- Hub-root product edits while `mode` is `product` (use the worktree)
- Any path under `sessions/` except `sessions/CODENAME/` and `sessions/_inbox/`
- `sessions/bindings/`, `sessions/context/`

## Hub sessions (`mode`: `hub`)

For template/hub maintenance only: set `"mode": "hub"` in `session.json` to allow edits at hub root (`scripts/`, `.cursor/`, docs). Product sessions stay `product`.

## On start

1. `./scripts/resolve-session.sh` — must print `CODENAME` for this chat.
2. Read this file, `session.json`, `TASKS.md`, `progress.json`.
3. If `tasks` is non-empty: `./scripts/ensure-worktrees.sh CODENAME` — work in `sessions/CODENAME/worktrees/<task-id>/`.
4. If `tasks` is empty: planning — update `TASKS.md` / `session.json`; run `ensure-worktrees.sh` when tasks are defined.

See [docs/WORKTREES.md](../../docs/WORKTREES.md).
