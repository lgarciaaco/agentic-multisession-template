# Changelog

All notable changes to this project will be documented in this file.

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
