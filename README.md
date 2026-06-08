# agentic-multisession-template

Project-agnostic **multi-session Cursor agent hub**. Each chat/tmux tab binds to a codename; hooks enforce scope and inject context.

Use **GitHub → Use this template**, or clone this repo as your hub.

## Prerequisites

- [Cursor](https://cursor.com) IDE
- Cursor **agent CLI** (`agent` on PATH)
- **Python** 3.10+
- **tmux** (optional terminal workflow)
- **PyYAML**: `pip install -r scripts/requirements.txt`

## Quick start (agentic-first)

**You:** clone, `cd`, start the agent.

```bash
git clone https://github.com/YOUR_ORG/agentic-multisession-template.git my-hub
cd my-hub
# Cursor: /start-work bootstrap
# or tmux after install: $(cat .hub-launcher)
```

**Agent:** reads [AGENTS.md](AGENTS.md), runs `./scripts/repos-status.sh`, asks which product repos to register (if any), runs setup scripts.

```bash
./scripts/repos-status.sh   # no_repos_yaml → agent asks for alias + git URL + branch
```

Hub-only (no product repos yet) is valid — `repos: {}` until you tell the agent what to add.

Optional manual install before tmux:

```bash
pip install -r scripts/requirements.txt
./scripts/install-workspace-agent.sh
```

## Architecture

```mermaid
flowchart TD
  clone[Clone_template] --> agent[Start_agent]
  agent --> status[repos-status.sh]
  status -->|ask_user| repos_yaml[repos.yaml]
  repos_yaml --> clone_repos[clone-repos.sh]
  clone_repos --> picker[Session_picker]
  picker --> worktrees[ensure-worktrees.sh]
  worktrees --> bind[bind_session_context]
  bind --> work[Product_in_worktrees]
```

**Sessions:** [SESSIONS.md](SESSIONS.md) · **Repos:** [docs/REPOS.md](docs/REPOS.md)

## Layout

```
.cursor/              hooks, rules, skills
repos.yaml.example    agent copies → repos.yaml (local)
repos/                reference clones (gitignored)
sessions/             codename dirs (gitignored)
scripts/              repos-status, clone-repos, ensure-worktrees, bind, …
docs/REPOS.md         registry spec
AGENTS.md             agent entry (read first)
```

## For agents

| Task | Doc |
|------|-----|
| First run / bootstrap | [AGENTS.md](AGENTS.md) · `.cursor/skills/bootstrap-hub` |
| Daily work | `.cursor/skills/session-orchestrator` · [SESSIONS.md](SESSIONS.md) |

## Env (optional)

| Variable | Default |
|----------|---------|
| `WORKSPACE_TMUX_PANE_OPTION` | `workspace-codename` |
| `WORKSPACE_TMUX_WINDOW_PREFIX` | Auto from hub slug; `""` disables |
| `WORKSPACE_AGENT_BIN` | `agent` |
| `WORKSPACE_AGENT_LAUNCHER` | `<slug-prefix>-agent` |

## Tests

```bash
python3 scripts/test_session_binding.py
```

## License

MIT — see [LICENSE](LICENSE).
