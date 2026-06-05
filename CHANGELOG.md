# Changelog

All notable changes to this project will be documented in this file.

## [0.3.0] - 2026-06-03

### Added

- **Git worktree isolation** — `scripts/ensure-worktrees.sh`; per-task checkout at `sessions/<codename>/worktrees/<id>/`
- `scripts/lib/hub_git.py` — fetch + `origin/<base>` for monorepo worktrees (no multi-repo / JIRA)
- `docs/WORKTREES.md` — task schema, modes, git layout
- `sessions/_codenames.example.yaml`, `sessions/index.example.json` — bootstrapped by `new-session.sh`
- Default product task in `sessions/_template/session.json` (`session/CODENAME` branch)
- Launcher runs `ensure-worktrees.sh` when hub has `.git`

### Changed

- **Product sessions** — hub root read-only; edits in worktree only (`mode: product`, default)
- **Hub sessions** — `mode: hub` allows `scripts/`, `.cursor/`, docs at root (template maintenance)
- Guard hook uses `guard_path_decision()` (art-style, no `repos/` / tickets)
- Session runtime gitignored: `sessions/*/`, `index.json`, `_codenames.yaml`, `worktrees/*`
- `BOUNDARIES.md`, `SESSIONS.md`, `AGENTS.md` updated for worktree workflow

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
