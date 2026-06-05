# Changelog

All notable changes to this project will be documented in this file.

## [0.3.0] - 2026-06-03

### Added

- **Git worktree isolation** — art-style `repos.yaml` + `repos/` reference clones + `sessions/<codename>/worktrees/<repo>/`
- `scripts/clone-repos.sh`, `scripts/lib/repos.py`, `repos.yaml.example`
- `scripts/ensure-worktrees.sh` — branches from `repos.yaml` via `tasks[].repo`
- `scripts/lib/hub_git.py` — fetch + `origin/<base>` (no JIRA / fork remotes)
- `docs/REPOS.md` — registry, one-repo = one entry (no separate monorepo layout)
- `sessions/_codenames.example.yaml`, `sessions/index.example.json` — bootstrapped by `new-session.sh`
- Default product task in `sessions/_template/session.json` (`session/CODENAME` branch)
- Launcher runs `ensure-worktrees.sh` when hub has `.git`

### Changed

- Guard: `repos/` read-only; writable worktrees + session metadata (optional `mode: hub`)
- Session runtime gitignored: `sessions/*/`, `repos/*`, `repos.yaml`, `index.json`, `_codenames.yaml`
- `BOUNDARIES.md`, `SESSIONS.md`, `AGENTS.md` updated for repos registry workflow

## [0.2.0] - 2026-06-05

### Added

- **Session inbox** — `sessions/_inbox/<target>.md`; `session-inbox.sh write/read`; injected on bind
- Guard allows `sessions/_inbox/` for all bound sessions

## [0.1.2] - 2026-06-05

### Added

- Auto tmux window prefix from hub slug (`immo-investor` → `immo-alpha`) via `hub-env.sh` + `session_binding`
- Re-run `install-workspace-agent.sh` after upgrade so the PATH launcher exports the prefix

### Changed

- `WORKSPACE_TMUX_WINDOW_PREFIX` unset → derived; explicit `""` still disables prefix

## [0.1.1] - 2026-06-05

### Added

- `.gitignore` — env, venv, pytest cache, logs; commented Node block for product forks
- `SESSIONS.md` — Git committed vs local table

### Fixed

- Session picker exits cleanly on Ctrl+C (exit 130, no traceback) — from 0.1.0 follow-up

## [0.1.0] - 2026-06-05

### Added

- Multi-session Cursor agent hub skeleton (hooks, rules, skills, commands)
- Per-project launcher install (`install-workspace-agent.sh` → `.hub-launcher`)
- Session binding: chat, tmux pane, sibling inheritance, interactive picker
- Bootstrap playbook (`CUSTOMIZE.md`, `bootstrap-hub` skill)
- Smoke tests (`scripts/test_session_binding.py`)
