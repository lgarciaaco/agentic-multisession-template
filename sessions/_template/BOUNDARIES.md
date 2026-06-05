# Session CODENAME

## Writable

- Project root
- `sessions/CODENAME/**`

## Forbidden

- `sessions/<other>/`
- `sessions/bindings/`, `sessions/context/`

On start: `./scripts/resolve-session.sh` → read `session.json`, `TASKS.md`, `progress.json`.
