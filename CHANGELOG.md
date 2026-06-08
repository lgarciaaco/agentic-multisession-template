# Changelog

All notable changes to this project will be documented in this file.

## [0.3.0] - 2026-06-03

### Added

- **repos.yaml registry** — multi-repo hub + `repos/` reference clones + `sessions/<codename>/worktrees/<repo>/`
- `scripts/clone-repos.sh`, `scripts/ensure-worktrees.sh`, `scripts/repos-status.sh`
- `scripts/lib/repos.py`, `scripts/lib/hub_git.py`, `repos.yaml.example`
- **Agent-first bootstrap** — `repos-status.sh` states; agent asks when registry missing/empty
- `docs/REPOS.md` — one product repo = one registry entry (N=1 or N=many)
- `sessions/_codenames.example.yaml`, `sessions/index.example.json`
- New sessions default to `tasks: []` until agent adds repos + tasks

### Changed

- Guard: `repos/` read-only; writable worktrees + session metadata
- Session runtime gitignored: `sessions/*/`, `repos/*`, `repos.yaml`, `index.json`, `_codenames.yaml`
- Launcher runs `clone-repos` + `ensure-worktrees` only when `repos-status` is `needs_clone` or `ready`
- `AGENTS.md`, skills, hooks, `SESSIONS.md` aligned to agentic bootstrap

## [0.2.0] - 2026-06-05

### Added

- **Session inbox** — `sessions/_inbox/<target>.md`; `session-inbox.sh write/read`; injected on bind
- Guard allows `sessions/_inbox/` for all bound sessions

## [0.1.2] - 2026-06-05

### Added

- Auto tmux window prefix from hub slug via `hub-env.sh` + `session_binding`
- Re-run `install-workspace-agent.sh` after upgrade so the PATH launcher exports the prefix

### Changed

- `WORKSPACE_TMUX_WINDOW_PREFIX` unset → derived; explicit `""` still disables prefix

## [0.1.1] - 2026-06-05

### Added

- `.gitignore` — env, venv, pytest cache, logs; commented Node block for product forks
- `SESSIONS.md` — Git committed vs local table

### Fixed

- Session picker exits cleanly on Ctrl+C (exit 130, no traceback)

## [0.1.0] - 2026-06-05

### Added

- Multi-session Cursor agent hub skeleton (hooks, rules, skills, commands)
- Per-project launcher install (`install-workspace-agent.sh` → `.hub-launcher`)
- Session binding: chat, tmux pane, sibling inheritance, interactive picker
- Bootstrap playbook (`CUSTOMIZE.md`, `bootstrap-hub` skill)
- Smoke tests (`scripts/test_session_binding.py`)
