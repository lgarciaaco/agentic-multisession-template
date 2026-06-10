# Session: CODENAME

Bound to codename `CODENAME` via `sessions/bindings/` (see `sessions/context/`).

## Writable

- `sessions/CODENAME/worktrees/**` — product code (git worktrees from `repos.yaml`)
- `sessions/CODENAME/session.json`, `TASKS.md`, `progress.json`, `workflow.json`
- `sessions/CODENAME/artifacts/**`, `sessions/CODENAME/reviews/**` — workflow and code-review state
- Cross-session: `sessions/_inbox/` via `./scripts/session-inbox.sh write`

## Read-only

- `repos/**` — reference clones; search and cite only (refresh: `./scripts/clone-repos.sh`)

## Forbidden

- Any edit under `repos/`
- Hub-root paths when bound — use worktrees for product code ([docs/REPOS.md](../../docs/REPOS.md) Guards)
- Any path under `sessions/` except `sessions/CODENAME/` and `sessions/_inbox/`
- `sessions/bindings/`, `sessions/context/`, `sessions/index.json`

## Enforced by hooks

Cursor path guards: [docs/REPOS.md](../../docs/REPOS.md) Guards (hub-root blocked when bound; registry pins unbound-only).

## Self-hosted hub

When `self_hosted: true` in `repos-status.sh`, see [docs/REPOS.md](../../docs/REPOS.md) Self-hosted hub.

## Hub sessions (`mode`: `hub`)

Label for CONTRIBUTING checklist and hub-upgrade workflows — **does not** unlock hub-root product edits. Product work still uses worktrees.

## On start

1. `./scripts/resolve-session.sh` — must print `CODENAME` for this chat.
2. Read `repos.yaml`, this file, `session.json`, `TASKS.md`, `progress.json`.
3. When work intent is clear: `./scripts/set-session-scope.sh CODENAME --title "…" --goal "…"` before product edits.
4. Read `docs/PROJECT.md` if present (project coding guidelines).
5. `./scripts/clone-repos.sh` if reference clones are missing or stale.
6. `./scripts/ensure-worktrees.sh CODENAME` when `tasks` is non-empty.

See [docs/REPOS.md](../../docs/REPOS.md).
