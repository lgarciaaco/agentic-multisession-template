# Customize this template (agent playbook)

**When:** User copies `agentic-multisession-template` to a new project directory and asks you to set it up or "bootstrap the hub."

**Goal:** Agent bootstraps after user clones template and starts Cursor. User does not run a manual checklist — the agent runs `./scripts/repos-status.sh`, asks for repos when needed, and executes scripts.

---

## Mandatory (every new project)

Run from the **new project root** (not the template repo path unless that is the project).

| Step | Action | Verify |
|------|--------|--------|
| 1 | `./scripts/repos-status.sh` — act on `state` (ask user if `no_repos_yaml` / `empty_registry`) | JSON printed |
| 2 | `pip install -r scripts/requirements.txt` | `python3 -c "import yaml"` |
| 3 | `./scripts/install-workspace-agent.sh` | `which $(cat .hub-launcher)` |
| 4 | Create/edit `repos.yaml`; `./scripts/clone-repos.sh` when user gave URLs | `state: ready` |
| 5 | Update `README.md` with project name when user cares | Human-readable |
| 6 | `python3 scripts/test_session_binding.py` && `python3 scripts/test_git_remotes.py` | All tests pass |
| 7 | `cp docs/PROJECT.md.example docs/PROJECT.md` — fill project name, stack, doc map (optional) | Project guidelines ready |

**Do not** skip install after copy — each hub gets its own command (e.g. `my-app` → `my-agent`) and config `~/.config/<project-slug>/hub`.

---

## Optional (only if user asks)

| Topic | What to change | Default (no action) |
|-------|----------------|---------------------|
| Tmux window prefix | `WORKSPACE_TMUX_WINDOW_PREFIX` | Auto from `.hub-slug` (`my-app` → `my-alpha`); `""` = bare codename |
| Tmux pane option | `WORKSPACE_TMUX_PANE_OPTION` | `workspace-codename` |
| Launcher name | `WORKSPACE_AGENT_LAUNCHER=my-agent ./scripts/install-workspace-agent.sh` | `<first-segment>-agent` (e.g. `my-app` → `my-agent`; long slug `agentic-multisession-template` → `agentic-agent` — override if undesired) |
| GitHub fork workflow | `github_fork_user` + `remote: github` in `repos.yaml`; `./scripts/configure-git-remotes.sh` | Push to `origin` on your own repos |
| Editor workspace | `./scripts/generate-workspace.sh` | Open hub + `repos/*` as multi-root in Cursor/VS Code |
| Codename pool | Edit `sessions/_codenames.example.yaml` before first `new-session.sh`, or local `_codenames.yaml` after | NATO `alpha`…`hotel` |
| Session template | `sessions/_template/` | New sessions start with `tasks: []` until agent adds tasks + repos |
| Domain skills | Add `.cursor/skills/<name>/SKILL.md`, register in `.cursor/skills/README.md` | See `.cursor/skills/README.md` (bootstrap, orchestrator, hub-upgrade, code-reviewer, session-end) |
| Domain rules | Add `.cursor/rules/*.mdc` | session-binding + orchestrator + session-boundary + agent-guidelines |
| Writable scope | Product: worktrees only; `repos/` read-only | default guard |

---

## Agent rules during bootstrap

- Work **only** in the hub root (this repo). Do not open other local repos unless the user explicitly asks.
- Each hub has its own launcher + `~/.config/<slug>/hub` — re-run install from **this** root after every copy.

---

## Do not customize (unless user explicitly requests)

- `scripts/lib/session_binding.py` / `session_cli.py` — core binding logic
- `.cursor/hooks.json` hook wiring
- Resolution order in `SESSIONS.md`
- `sessions/bindings/` and `sessions/context/` — gitignored runtime state

---

## After bootstrap

1. Delete or archive this file (`CUSTOMIZE.md`) if the user wants a clean repo — or keep it as reference.
2. When user gave repos and `repos-status` is `ready`: `$(cat .hub-launcher)` → **new** session → add tasks → `ensure-worktrees` → work under `sessions/<codename>/worktrees/<repo>/`.
3. Mark template task **done** when mandatory steps pass and docs name the project.

---

## Quick copy command (for user)

```bash
cp -R /path/to/agentic-multisession-template /path/to/my-project
cd /path/to/my-project
# then run mandatory steps above
```
