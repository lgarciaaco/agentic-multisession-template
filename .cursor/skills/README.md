# Skills

| Skill | Trigger | Scripts |
|-------|---------|---------|
| [bootstrap-hub](bootstrap-hub/SKILL.md) | first run, bootstrap hub | `repos-status.sh`, `clone-repos.sh`, `install-workspace-agent.sh` |
| [session-orchestrator](session-orchestrator/SKILL.md) | start work, `/start-work` | `repos-status.sh`, `resolve-session.sh`, `bind-session.sh`, `new-session.sh`, `set-session-scope.sh`, `ensure-worktrees.sh`, `sync-session.sh`, `prompt-session-start.sh` |
| [session-end](session-end/SKILL.md) | end session, `/end-session` | `end-session.sh` |
| [hub-upgrade](hub-upgrade/SKILL.md) | template version, upgrade hub | `hub-status.sh`, `hub-upgrade.sh` |
| [code-reviewer](code-reviewer/SKILL.md) | code review, audit scope | (orchestrator spawns specialist agents; see skill) |
| [workflow-orchestrator](workflow-orchestrator/SKILL.md) | `/workflow`, `/workflow status`, accept/reopen gates | `workflow-plan-synthesize.py`, `workflow-accept-plan.sh`, `workflow-begin-code-review.py`, `workflow-code-review-*`, `workflow-write-delivery-report.py`, `workflow-reopen-*.py`; state in `workflow.json` |

Tmux: `$(cat .hub-launcher)` — not bare `agent`.

Agent entry: [AGENTS.md](../../AGENTS.md)
