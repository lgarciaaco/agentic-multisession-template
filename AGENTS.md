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
3. **Scope metadata** — when work intent is clear, run `./scripts/set-session-scope.sh <codename> --title "…" --goal "…"` before the first product edit (see [SESSIONS.md](SESSIONS.md))
4. `session.json` tasks need `"repo": "<alias>"` matching `repos.yaml`; then `./scripts/ensure-worktrees.sh <codename>`
5. Edit product in `sessions/<codename>/worktrees/<repo>/` only
6. `./scripts/sync-session.sh <codename>` after other metadata edits

Optional session fields in `session.json`: **`next`** (resume hint); per-task **`pr`**, **`ci`**, **`note`** (shown in chat context). See [docs/REPOS.md](docs/REPOS.md).

When `repos.yaml` uses **GitHub fork workflow** (`github_fork_user`, `remote: github`): push feature branches to **`fork`**, not upstream `origin`. Run `./scripts/configure-git-remotes.sh` if remotes look wrong. See `.cursor/rules/git-fork-pr.mdc`.

Regenerate a multi-root editor workspace: `./scripts/generate-workspace.sh` → `<hub-slug>.code-workspace`.

## End

**end session** / **`/end-session`** → `.cursor/skills/session-end/SKILL.md` → `./scripts/end-session.sh`

## Hub template upgrade

Ask **"Is there a new template version?"** → `./scripts/hub-status.sh` → explain hub changes + session notes in plain language.

Say **"Upgrade"** → `.cursor/skills/hub-upgrade/SKILL.md` → `./scripts/hub-upgrade.sh --yes` (hub layer only; keeps `repos.yaml` and session folders).

Installed version: `.hub-version` · upstream check: `./scripts/hub-status.sh`

## Reference

[SESSIONS.md](SESSIONS.md) · [docs/REPOS.md](docs/REPOS.md) · bound `BOUNDARIES.md`

## Scope

- **Product:** `sessions/<codename>/worktrees/**` + session metadata; `repos/` read-only
- **Forbidden:** other `sessions/<other>/`, edits under `repos/`

## Coding guidelines

Two levels — read together:

| Level | Source |
|-------|--------|
| **Template** | `.cursor/rules/agent-guidelines.mdc` — docs sync + test minimum (always on) |
| **Hub PRs** | `.cursor/rules/hub-contributing.mdc` — always injected (`alwaysApply: true`); follow only when `session.json` `"mode": "hub"` |
| **Project** | `docs/PROJECT.md` — copy from [docs/PROJECT.md.example](docs/PROJECT.md.example) and fill stack, doc map, test commands |

Session context lists which guideline files exist on bind. Optional `guidelines:` in `repos.yaml` — see [docs/REPOS.md](docs/REPOS.md).

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
- **Fork workflow** (when configured in `repos.yaml`): push to `fork`, PR with `--head {github_fork_user}:branch` — [CONTRIBUTING.md](CONTRIBUTING.md), `.cursor/rules/git-fork-pr.mdc`
