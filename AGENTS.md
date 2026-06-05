# Agent guide

## Template bootstrap

If this hub was just copied from **agentic-multisession-template** and not yet customized: read [CUSTOMIZE.md](CUSTOMIZE.md), run mandatory steps, update `README.md` / this file for the project name, then continue below.

---

## Start

**Tmux / terminal:** `$(cat .hub-launcher)` after install — session list by default (`--reuse` to keep tab binding). Not bare `agent`.

**Cursor chat:** **start work** / **`/start-work`** → `.cursor/skills/session-orchestrator/SKILL.md`

1. `./scripts/resolve-session.sh` or picker → bind codename
2. `./scripts/ensure-worktrees.sh <codename>` if worktree missing (launcher does this when `.git` exists)
3. Read `sessions/<codename>/TASKS.md`, `session.json`; edit product code in `sessions/<codename>/worktrees/**`
4. `./scripts/sync-session.sh <codename>` after metadata edits

## End

**end session** / **`/end-session`** → `.cursor/skills/session-end/SKILL.md` → `./scripts/end-session.sh`

## First read

[SESSIONS.md](SESSIONS.md) · [docs/WORKTREES.md](docs/WORKTREES.md) · bound `BOUNDARIES.md`

## Scope

- **Product session (`mode: product`):** `sessions/<codename>/worktrees/**` + session metadata; hub root read-only
- **Hub session (`mode: hub`):** hub root + `sessions/<codename>/` (template maintenance only)
- **Forbidden:** other `sessions/<other>/`

## Skills

| | Path |
|-|------|
| Bootstrap | [CUSTOMIZE.md](CUSTOMIZE.md) |
| Start | `.cursor/skills/session-orchestrator` |
| End | `.cursor/skills/session-end` |

## Cross-session inbox

Leave a note for another session: `./scripts/session-inbox.sh write <from> <to> "message"`.  
On bind, the target session's inbox is injected into context. Read anytime: `session-inbox.sh read <codename>`.

## Git / PRs

- May open branches and PRs; fix CI if tests fail
- **Never** `gh pr merge --auto` or enable auto-merge
- **Never** merge or push to `main` unless the user explicitly asks
- See [CONTRIBUTING.md](CONTRIBUTING.md) Pull requests section
