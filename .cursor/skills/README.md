# Skills

| Skill | Trigger | Scripts |
|-------|---------|---------|
| [bootstrap-hub](bootstrap-hub/SKILL.md) | first run, bootstrap hub | `repos-status.sh`, `clone-repos.sh`, `install-workspace-agent.sh` |
| [session-orchestrator](session-orchestrator/SKILL.md) | start work, `/start-work` | `repos-status.sh`, `resolve-session.sh`, `bind-session.sh`, `new-session.sh`, `ensure-worktrees.sh`, `sync-session.sh`, `prompt-session-start.sh` |
| [session-end](session-end/SKILL.md) | end session, `/end-session` | `end-session.sh` |
| [code-reviewer](code-reviewer/SKILL.md) | code review, audit scope | (orchestrator spawns specialist agents; see skill) |

Tmux: `$(cat .hub-launcher)` — not bare `agent`.

Agent entry: [AGENTS.md](../../AGENTS.md)
