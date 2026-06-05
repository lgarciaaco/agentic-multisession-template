# Customize this template (agent playbook)

**When:** User copies `agentic-multisession-template` to a new project directory and asks you to set it up or "bootstrap the hub."

**Goal:** Turn the generic skeleton into a named project hub. Session binding, hooks, and scripts work out of the box — customization is mostly naming, install, and optional domain additions.

---

## Mandatory (every new project)

Run from the **new project root** (not the template repo path unless that is the project).

| Step | Action | Verify |
|------|--------|--------|
| 1 | Confirm hub root; `cp repos.yaml.example repos.yaml` and set `clone` URL | `pwd` |
| 2 | `pip install -r scripts/requirements.txt` | `python3 -c "import yaml"` |
| 3 | `./scripts/install-workspace-agent.sh` | `which $(cat .hub-launcher)` and `cat ~/.config/$(cat .hub-slug)/hub` equals this project root |
| 4 | Update `README.md` — replace template title with **project name** and one-line purpose | Human-readable |
| 5 | Update `AGENTS.md` — remove "template bootstrap" block; add project-specific first-read links if any | Agent entry |
| 6 | `python3 scripts/test_session_binding.py` | All tests pass |

**Do not** skip install after copy — each hub gets its own command (e.g. `my-app` → `my-agent`) and config `~/.config/<project-slug>/hub`.

---

## Optional (only if user asks)

| Topic | What to change | Default (no action) |
|-------|----------------|---------------------|
| Tmux window prefix | `WORKSPACE_TMUX_WINDOW_PREFIX` | Auto from `.hub-slug` (`immo-investor` → `immo-alpha`); `""` = bare codename |
| Tmux pane option | `WORKSPACE_TMUX_PANE_OPTION` | `workspace-codename` |
| Launcher name | `WORKSPACE_AGENT_LAUNCHER=my-agent ./scripts/install-workspace-agent.sh` | `<first-segment>-agent` (e.g. `my-app` → `my-agent`; long slug `agentic-multisession-template` → `agentic-agent` — override if undesired) |
| Codename pool | Edit `sessions/_codenames.example.yaml` before first `new-session.sh`, or local `_codenames.yaml` after | NATO `alpha`…`hotel` |
| Session template | `sessions/_template/BOUNDARIES.md`, `TASKS.md`, `session.json` | Default `product` task + `session/CODENAME` branch |
| Repos | `repos.yaml` + `./scripts/clone-repos.sh` before worktrees | See [docs/REPOS.md](docs/REPOS.md) |
| Domain skills | Add `.cursor/skills/<name>/SKILL.md`, register in `.cursor/skills/README.md` | session-orchestrator + session-end only |
| Domain rules | Add `.cursor/rules/*.mdc` | session-binding + orchestrator + session-boundary |
| Writable scope | Product: worktrees only; `repos/` read-only; optional `mode: hub` | art-style |

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
2. `./scripts/clone-repos.sh` → `$(cat .hub-launcher)` → pick **new** → work under `sessions/<codename>/worktrees/project/`.
3. Mark template task **done** when mandatory steps pass and docs name the project.

---

## Quick copy command (for user)

```bash
cp -R /path/to/agentic-multisession-template /path/to/my-project
cd /path/to/my-project
# then run mandatory steps above
```
