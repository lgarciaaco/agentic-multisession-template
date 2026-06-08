# Changelog

All notable changes to this project will be documented in this file.

## [0.5.0] - 2026-06-08

### Added

- **Agent coding guidelines** — `.cursor/rules/agent-guidelines.mdc` (docs sync + test minimum) and `.cursor/rules/hub-contributing.mdc` (hub-mode PR checklist)
- [docs/PROJECT.md.example](docs/PROJECT.md.example) — project-specific guideline scaffold (copy to local `docs/PROJECT.md`)
- Optional `guidelines:` pointers in `repos.yaml` — `load_guidelines()` in `scripts/lib/repos.py`
- Session context **Guidelines** section on bind — lists template, project, and worktree doc paths when present
- **Themed codename pools** — `active_pool` in `sessions/_codenames.yaml`; example `bg3` pool in `sessions/_codenames.example.yaml`

### Changed

- [AGENTS.md](AGENTS.md), [SESSIONS.md](SESSIONS.md), [CUSTOMIZE.md](CUSTOMIZE.md), [docs/REPOS.md](docs/REPOS.md) — document two-level guideline hierarchy
- `sessions/_template/BOUNDARIES.md` — read `docs/PROJECT.md` on start when present
- `new-session.sh` — codename allocation moved to `scripts/lib/session_binding.py` (testable)

### Fixed

- **Exhausted codename pool** — auto-expand active pool with NATO continuation (`india`, `juliet`, …) instead of failing when all starter names are used
- **Session picker traceback** — `new` choice shows script error message and re-prompts instead of `CalledProcessError`
- **Empty session title** — new sessions default `title` to codename; interactive picker prompts to customize

### Session notes

**Impact:** optional

- Existing sessions keep working; copy `docs/PROJECT.md.example` → `docs/PROJECT.md` when you want project-level guidelines
- Hub upgrade delivers new rules and docs; local `docs/PROJECT.md` is not overwritten

## [0.4.0] - 2026-06-08

### Added

- **In-place hub upgrade** — `.hub-version`, `./scripts/hub-status.sh`, `./scripts/hub-upgrade.sh`
- `scripts/lib/hub_upgrade.py` — compare installed vs upstream template; refresh hub layer without touching product repos or session history
- `.hub-upstream.example` — optional override when this hub's git origin is not the template repo
- `hub-upgrade` agent skill — plain-language version check and upgrade-on-request flow

### Changed

- `CHANGELOG.md` — each release includes **Session notes** with impact (`none` / `optional` / `required`)

### Session notes

**Impact:** none

- Existing sessions keep working; no session folder edits required for this release
- After upgrade, re-run `./scripts/install-workspace-agent.sh` if the launcher or tmux prefix behavior changed

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

### Session notes

**Impact:** optional

- Older sessions may still assume edits at project root — product work now belongs under `sessions/<codename>/worktrees/<repo>/`
- Add `"repo": "<alias>"` to each task in `session.json`, then run `./scripts/ensure-worktrees.sh <codename>`
- Refresh `BOUNDARIES.md` from `sessions/_template/BOUNDARIES.md` if your session copy predates worktrees

## [0.2.0] - 2026-06-05

### Added

- **Session inbox** — `sessions/_inbox/<target>.md`; `session-inbox.sh write/read`; injected on bind
- Guard allows `sessions/_inbox/` for all bound sessions

### Session notes

**Impact:** optional

- Sessions created before inbox existed won't mention cross-session notes in their boundaries — no breakage
- Use `./scripts/session-inbox.sh write alpha bravo "message"` when coordinating across Cursor windows

## [0.1.2] - 2026-06-05

### Added

- Auto tmux window prefix from hub slug via `hub-env.sh` + `session_binding`
- Re-run `install-workspace-agent.sh` after upgrade so the PATH launcher exports the prefix

### Changed

- `WORKSPACE_TMUX_WINDOW_PREFIX` unset → derived; explicit `""` still disables prefix

### Session notes

**Impact:** none

- tmux window naming only; session folders unchanged

## [0.1.1] - 2026-06-05

### Added

- `.gitignore` — env, venv, pytest cache, logs; commented Node block for product forks
- `SESSIONS.md` — Git committed vs local table

### Fixed

- Session picker exits cleanly on Ctrl+C (exit 130, no traceback)

### Session notes

**Impact:** none

- Documentation and picker behavior only

## [0.1.0] - 2026-06-05

### Added

- Multi-session Cursor agent hub skeleton (hooks, rules, skills, commands)
- Per-project launcher install (`install-workspace-agent.sh` → `.hub-launcher`)
- Session binding: chat, tmux pane, sibling inheritance, interactive picker
- Bootstrap playbook (`CUSTOMIZE.md`, `bootstrap-hub` skill)
- Smoke tests (`scripts/test_session_binding.py`)

### Session notes

**Impact:** none

- Initial template; no prior sessions to migrate
