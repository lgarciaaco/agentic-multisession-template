# Skills

| Skill | Trigger | Scripts |
|-------|---------|---------|
| [bootstrap-hub](bootstrap-hub/SKILL.md) | first run, bootstrap hub | `repos-status.sh`, `clone-repos.sh`, `install-workspace-agent.sh` |
| [session-orchestrator](session-orchestrator/SKILL.md) | start work, `/start-work` | `resolve-session.sh`, `bind-session.sh`, `set-session-scope.sh`, `ensure-worktrees.sh`, … |
| [workflow-orchestrator](workflow-orchestrator/SKILL.md) | `/workflow`, accept/reopen gates | `workflow-plan-synthesize.py`, `workflow-accept-plan.sh`, `workflow-code-review-*`, … |
| [code-reviewer](code-reviewer/SKILL.md) | code review, quality gate | Task specialists + synthesizer |
| [session-end](session-end/SKILL.md) | end session, `/end-session` | `end-session.sh` |
| [hub-upgrade](hub-upgrade/SKILL.md) | template version, upgrade hub | `hub-status.sh`, `hub-upgrade.sh` |
| [write-like-a-human](write-like-a-human/SKILL.md) | human-facing brief/report/PR text | — |
| [skill-optimizer](skill-optimizer/SKILL.md) | streamline hub skills | — |

Tmux: `$(cat .hub-launcher)` — not bare `agent`.

Agent entry: [AGENTS.md](../../AGENTS.md)

## Subagent isolation

Workflow plan loop and code review specialists require **Task subagents**. Conductors spawn roles; they do not inline plan, plan review, or specialist findings. See workflow-orchestrator [rules/conductor.md](workflow-orchestrator/rules/conductor.md) and code-reviewer SKILL.
