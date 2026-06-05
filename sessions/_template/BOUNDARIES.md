# Session CODENAME

## Writable

- Project root
- `sessions/CODENAME/**`

## Forbidden

- `sessions/<other>/` (except cross-session inbox — see below)
- `sessions/bindings/`, `sessions/context/`

## Cross-session messages

Use `./scripts/session-inbox.sh write <from> <to> "message"` — writes to `sessions/_inbox/<to>.md`. Target session sees it on bind or via `session-inbox.sh read`.

On start: `./scripts/resolve-session.sh` → read `session.json`, `TASKS.md`, `progress.json`.
