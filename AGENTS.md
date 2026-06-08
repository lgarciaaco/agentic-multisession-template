# Agent guide

## First run (agentic bootstrap)

User cloned **agentic-multisession-template**, `cd` here, started you. **You** drive setup.

```bash
./scripts/repos-status.sh    # always start here — JSON state
```

| `state` | Your move |
|---------|-----------|
| `no_repos_yaml` / `empty_registry` | **Ask user** for repos (alias + git URL + branch each). Create/edit `repos.yaml`. |
| `needs_clone` | `./scripts/clone-repos.sh` |
| `ready` | Sessions + worktrees (below) |

Full playbook: `.cursor/skills/bootstrap-hub/SKILL.md` · [docs/REPOS.md](docs/REPOS.md)

Hub install if needed: `pip install -r scripts/requirements.txt` && `./scripts/install-workspace-agent.sh`

---

## Start work

**Tmux:** `$(cat .hub-launcher)` — not bare `agent`.

**Cursor:** **start work** / **`/start-work`** → `.cursor/skills/session-orchestrator/SKILL.md`

1. `./scripts/repos-status.sh` — if not `ready` and user wants **product** work, bootstrap repos first (ask if missing).
2. `./scripts/resolve-session.sh` or picker → bind codename
3. `session.json` tasks need `"repo": "<alias>"` matching `repos.yaml`; then `./scripts/ensure-worktrees.sh <codename>`
4. Edit product in `sessions/<codename>/worktrees/<repo>/` only
5. `./scripts/sync-session.sh <codename>` after metadata edits

## End

**end session** / **`/end-session`** → `.cursor/skills/session-end/SKILL.md` → `./scripts/end-session.sh`

## Hub template upgrade

Ask **"Is there a new template version?"** → `./scripts/hub-status.sh` → explain hub changes + session notes in plain language.

Say **"Upgrade"** → `.cursor/skills/hub-upgrade/SKILL.md` → `./scripts/hub-upgrade.sh --yes` (hub layer only; keeps `repos.yaml` and session folders).

Installed version: `.hub-version` · upstream check: `./scripts/hub-status.sh`

## Reference

[SESSIONS.md](SESSIONS.md) · [docs/REPOS.md](docs/REPOS.md) · bound `BOUNDARIES.md`

**Project guidelines:** read [docs/PROJECT.md](docs/PROJECT.md) when present (doc sync, tests, stack conventions for product worktrees).

## Scope

- **Product:** `sessions/<codename>/worktrees/**` + session metadata; `repos/` read-only
- **Forbidden:** other `sessions/<other>/`, edits under `repos/`

## Skills

| | Path |
|-|------|
| Bootstrap | `.cursor/skills/bootstrap-hub` |
| Start | `.cursor/skills/session-orchestrator` |
| Code review | `.cursor/skills/code-reviewer` |
| Hub upgrade | `.cursor/skills/hub-upgrade` |
| End | `.cursor/skills/session-end` |

## Cross-session inbox

`./scripts/session-inbox.sh write <from> <to> "message"` · read on bind or `session-inbox.sh read <codename>`

## Git / PRs

- **Never** `gh pr merge --auto` or auto-merge
- **Never** merge/push `main` unless user explicitly asks
- [CONTRIBUTING.md](CONTRIBUTING.md)
