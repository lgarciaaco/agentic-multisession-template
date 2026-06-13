# Skills

| Skill | Trigger | Scripts |
|-------|---------|---------|
| [bootstrap-hub](bootstrap-hub/SKILL.md) | first run, bootstrap hub | `repos-status.sh`, `clone-repos.sh`, `install-workspace-agent.sh` |
| [session-start](session-start/SKILL.md) | start work, `/start-work` | `resolve-session.sh`, `bind-session.sh`, `set-session-scope.sh`, `ensure-worktrees.sh`, … |
| [sessions-orchestrator](sessions-orchestrator/SKILL.md) | `/sessions-orchestrator` | `program-decompose.py`, `program-monitor.py`, `program-route-feedback.py`, … |
| [workflow-orchestrator](workflow-orchestrator/SKILL.md) | `/workflow-orchestrator`, accept/reopen gates | `workflow-plan-synthesize.py`, `workflow-accept-plan.sh`, `workflow-code-review-*`, … |
| [code-reviewer](code-reviewer/SKILL.md) | code review, quality gate | Task specialists + synthesizer |
| [session-end](session-end/SKILL.md) | end session, `/end-session` | `end-session.sh` |
| [hub-upgrade](hub-upgrade/SKILL.md) | template version, upgrade hub | `hub-status.sh`, `hub-upgrade.sh` |
| [write-like-a-human](write-like-a-human/SKILL.md) | human-facing brief/report/PR text | — |
| [skill-optimizer](skill-optimizer/SKILL.md) | streamline hub skills | — |
| [loop](loop/SKILL.md) | `/loop [interval] <prompt>`, inbox gate polling | background shell + sentinel |

Tmux: `$(cat .hub-launcher)` — not bare `agent`.

Agent entry: [AGENTS.md](../../AGENTS.md)

## Subagent isolation

Workflow plan loop and code review specialists require **Task subagents**. Program parent **check children** spawns one Task(child-reviewer) per active child. Conductors spawn roles; they do not inline plan, plan review, multi-child gate review, or specialist findings. See workflow-orchestrator [rules/conductor.md](workflow-orchestrator/rules/conductor.md), [sessions-orchestrator/SKILL.md](sessions-orchestrator/SKILL.md), and code-reviewer SKILL.
