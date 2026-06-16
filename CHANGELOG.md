# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## [1.0.0-rc.5] - 2026-06-16

Program routing hardening and workflow consolidation — idempotent gate guards,
shared helper refactors, gate registry, and doc alignment (#73–#88).

### Added

- **Idempotent route feedback guards** — `program-route-feedback.py` blocks duplicate gate commands, smuggled gate strings in corrections, and already-accepted re-sends (#84, #88)
- **Gate metadata registry** — shared gate constants and phase lookups consolidated into `scripts/lib/gate_registry.py` (#75)
- **Gate registry drift tests** — guards ensuring CLI scripts, workflow phases, and route feedback stay in sync with the registry (#83)

### Changed

- **Workflow helper consolidation** — shared plan/code-review/PR helpers refactored into common modules; reduced duplication across phase scripts (#77, #81)
- **Program monitor snapshot** — read-only snapshot split from context refresh; child workflow state reused in route checks (#76, #86)
- **Hub-upgrade defaults** — `DEFAULT_UPSTREAM` genericized; RC smoke-test docs updated (#74)
- **Docs alignment** — program orchestrator, workflow, sessions-orchestrator skill, and inbox gate docs aligned with shipped classify-only and tmux routing semantics (#73, #79, #82, #87)

### Fixed

- **Tmux pane routing** — hardened pane lookup for parent gate feedback (#80)
- **Inbox gate rejected markers** — rejected items kept in pending queue instead of silently dropped (#78)
- **Route normalizer** — standalone poll docs and route input normalization for consistent gate matching (#85)

### Session notes

**Impact:** optional

- Existing sessions keep working; no session folder edits required
- Program parent sessions benefit from idempotent route guards — duplicate gate commands are now safely skipped
- Hub upgrade: `./scripts/hub-upgrade.sh` picks up rc.5 from upstream tag

## [1.0.0-rc.4] - 2026-06-13

Program orchestrator production pass (xray) — six child PRs merged (#66–#71, #68).

### Added

- **`session-start` skill** — rename from `session-orchestrator`; `/start-work` entry distinct from `sessions-orchestrator`
- **Program tmux routing** — parent gate feedback and corrections via `tmux send-keys` to child panes; `pane_id` persisted at bootstrap; `program-route-feedback.py` / `--message` for free-text
- **Completed-child tab cleanup** — `program_monitor` closes child tmux windows when workflow phase is `completed`; `active_children[].status` synced
- **Non-interactive git editors** — `GIT_EDITOR`/`EDITOR` in child tmux launch; `scripts/workflow-git-rebase.sh` for CI/rebase paths
- **Leaks reviewer** — code-reviewer specialist (`triggers.leaks`) for secrets, PII, hardcoded identifiers; synthesizer FAIL wiring
- **Cross-child gate review** — `sibling_program_context` in monitor JSON; child-reviewer cross-child checks; slim one-screen parent **Check children** chat; detail in `program-status.md` via `--reviews-json`
- **Infra YAML reviewer** — code-reviewer pipeline specialist for Ansible, GitHub Actions, and deploy manifests (`triggers.infra`)

### Changed

- **Program parent routing** — removed program-parent inbox auto-apply (`write_inbox_program_route`, inbox gate authorization for program gates); standalone session inbox unchanged
- **Skill optimizer docs** — hub integration in `AGENTS.md` / skills README; no mandated percent line-reduction target
- **`AGENTS.md`**, **`docs/PROGRAM_ORCHESTRATOR.md`**, **`sessions-orchestrator`** skill — tmux routing, slim status format, merge-boundary notes for parallel program children

### Session notes

**Impact:** optional

- Refresh stale `BOUNDARIES.md` from template if sessions predate tmux program routing
- Parent program sessions: use `tmux send-keys` for gate commands; inbox gate polling no longer applies to program parent→child routing
- Hub upgrade: `./scripts/hub-upgrade.sh` picks up rc.4 from upstream tag

## [1.0.0-rc.3] - 2026-06-11

### Added

- **PR creation phase** (`pr_creation`) — auto commit + draft PR after code review PASS; records PR URL on task; uses `git-commit` and `pr-create` skills
- **CI observe loop** (`ci_observe`) — polls CI, rebases on merge conflicts, fixes test failures (code-fixer pattern), force-pushes; 5-iteration cap before escalation
- **`git-commit` skill** (`.cursor/skills/git-commit/`) — generic conventional-commit workflow; branch safety and staging checks
- **`pr-create` skill** (`.cursor/skills/pr-create/`) — generic draft PR creation with fork workflow support and `repos.yaml` branch targeting
- **`pr_target_branch`** field in `repos.yaml` — optional per-repo PR base branch (falls back to `default_branch`)
- `scripts/lib/workflow_pr_creation.py`, `scripts/lib/workflow_ci_observe.py` — phase logic
- `scripts/workflow-advance-pr-creation.py`, `scripts/workflow-ci-observe-advance.py` — CLIs
- `rules/ci-fixer.md` — conductor rules for CI failure resolution
- `references/pr-creation.md`, `references/ci-observe-loop.md` — phase documentation

### Changed

- BOUNDARIES template, SESSIONS.md, docs/REPOS.md, and inbox README aligned: bound sessions cannot edit `sessions/_inbox/` paths directly; cross-session messages via `./scripts/session-inbox.sh write` only; REPOS Guards split into writable vs blocked-when-bound subsections
- **`sync-session.sh`** — for sessions without `workflow.json`, rewrites `TASKS.md` ## Tasks from `session.json` tasks (empty array → table header rows plus empty-state note, no task data rows)
- **`set-session-scope.sh --goal`** — backfills `progress.json` `description` when blank; preserves existing description
- **`sessions/_template/TASKS.md`** — removes phantom pending row; documents empty tasks state
- `advance_code_review_loop` on PASS now sets phase `pr_creation` (was `delivery`)
- `sessions/_template/workflow.json` version 2: adds `loops.pr_creation` and `loops.ci_observe`
- `workflow_resume.py` returns next-action hints for `pr_creation` and `ci_observe` phases
- Workflow pipeline overview: `code_review PASS → pr_creation → ci_observe → delivery`
- `AGENTS.md`, `docs/WORKFLOW.md`, workflow-schema reference updated for new phases

## [1.0.0-rc.1] - 2026-06-10

First stable candidate — workflow pipeline, path guards, skills/docs hygiene since `0.6.0`.

### Added

- **workflow-orchestrator** skill — role rules, `SKILL.md`, `workflow.json` schema, artifact templates under `sessions/_template/artifacts/`
- **`format_workflow_section`** — injects workflow phase, gates, loops, artifact paths, and **Resume** hint into chat context
- **Plan loop** — `scripts/lib/workflow_plan.py`, `scripts/workflow-plan-synthesize.py`; autonomous REVISE→APPROVE synthesis and `pr-NNN` persistence
- **Accept plan** — `scripts/workflow-accept-plan.sh`; task sync from `action-plan.md`; workflow gates block worktree edits until plan accepted
- **Code review loop** — `scripts/lib/workflow_code_review.py`, enrich/advance/begin CLIs; intent reviewer reads `action-plan.md` acceptance
- **Delivery + resume** — `workflow-write-delivery-report.py`, reopen CLIs, `workflow_next_action()` for `/workflow` continuation
- **Hub docs + tests** — `test_workflow_plan_reviewer_rules.py`; expanded pre-PR suite; walkthrough in `docs/WORKFLOW.md`
- **Self-hosted hub detection** — `repos-status.sh` reports `self_hosted` when a registry clone URL matches hub `origin`
- Session-start nudge when self-hosted but worktree is missing
- **Structure reviewer** — code-reviewer pipeline specialist for layout and cross-file consistency
- **Generic `docs/PROJECT.md`** — shipped template replaces domain-specific project copy

### Changed

- `AGENTS.md`, `SESSIONS.md`, `.cursor/skills/README.md`, `orchestrator.mdc`, `CONTRIBUTING.md` — `/workflow` pipeline, trigger routing, inbox demoted to optional
- Path guards block hub-root product paths for all bound sessions (`mode: hub` no longer unlocks `scripts/`, `.cursor/`, or docs)
- Hub-root registry pins (`repos.yaml`, `.hub-version`, `.hub-upstream`) blocked for bound sessions (unbound-only)
- `normalize_git_url` handles `ssh://` URLs; session-start emits scope and worktree nudges together
- Self-hosted playbook in `docs/REPOS.md`, bootstrap/orchestrator skills, and `BOUNDARIES.md`
- **Skills audit (PR-1)** — all six hub skills reviewed; workflow conductor rules mandate Task subagents for plan author/reviewer (no inline plan writes)
- **Doc consolidation (PR-2+3)** — canonical cross-links across `AGENTS.md`, `SESSIONS.md`, `CUSTOMIZE.md`, and `README.md`; milestone/WIP jargon removed from shipped skill and hub docs

### Fixed

- **`parse_action_plan_tasks`** — acceptance cells containing pipe characters no longer break task sync (+ unit test)

### Session notes

**Impact:** optional

- **Workflow:** `/workflow` for single-chat delivery; resume from `workflow.json` phase
- Self-hosted hubs: add `tasks[].repo`, run `ensure-worktrees.sh`, edit worktree — not hub root
- Hub layer refresh: `./scripts/hub-upgrade.sh` only
- Refresh `BOUNDARIES.md` from `sessions/_template/BOUNDARIES.md`

## [0.6.0] - 2026-06-09

### Added

- **`set-session-scope.sh`** — set session `title`, `TASKS.md` goal, and optional `next` in one command; refreshes index and chat context
- Session-start hook nudge when scope is still thin (no title/goal/next/tasks)

### Changed

- session-start skill and session-binding rule — agents set scope metadata before product edits when work intent is clear
- `resume_session_on_bind` backfills empty legacy titles to codename
- SESSIONS.md Cursor workflow, `_template/BOUNDARIES.md`, and `docs/REPOS.md` document scope command

### Fixed

- **`set-session-scope.sh`** — sanitize `--goal` before TASKS.md and chat context; hook no longer crashes on invalid codenames; placeholder tasks no longer suppress thin-scope nudge

### Session notes

**Impact:** optional

- Existing sessions keep working; agents are nudged to set title/goal when scope is empty
- After upgrade, refresh `BOUNDARIES.md` from `sessions/_template/BOUNDARIES.md` if your session copy predates the scope step

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
- Guard allowed `sessions/_inbox/` path edits for bound sessions *(documentation corrected in 1.0.0-rc.3 — hooks block direct edits; CLI only)*

### Session notes

**Impact:** optional

- Sessions created before inbox existed won't mention cross-session notes in their boundaries — no breakage
- Use `./scripts/session-inbox.sh write <from> <to> "message"` when coordinating across Cursor windows (message lands in `sessions/_inbox/<to>.md`)

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
