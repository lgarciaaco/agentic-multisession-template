# Workflow orchestrator

Single-session pipeline: **Problem → Plan → Code → Review**. One chat, three user gates.

Entry: [SKILL.md](SKILL.md)

## Roles

| Role | Rules | Agent procedure |
|------|-------|-----------------|
| Analyst | [rules/problem-analyst.md](rules/problem-analyst.md) | parent agent (conductor) |
| Plan author | [rules/plan-author.md](rules/plan-author.md) | [agents/plan-author.md](agents/plan-author.md) — **Task subagent only** |
| Plan reviewer | [rules/plan-reviewer.md](rules/plan-reviewer.md) | [agents/plan-reviewer.md](agents/plan-reviewer.md) — **Task subagent only** |
| Conductor | [rules/conductor.md](rules/conductor.md) | inline — must not inline plan author/reviewer |
| Code review | [../code-reviewer/SKILL.md](../code-reviewer/SKILL.md) | subroutine |

## Subagent isolation

Plan loop roles run in **separate Task subagents**. The conductor spawns them, writes the workspace manifest, and runs `workflow-plan-synthesize.py`. See [rules/conductor.md](rules/conductor.md) **Subagent isolation (mandatory)**.

## References (agent internals)

- [references/workflow-schema.md](references/workflow-schema.md)
- [references/workspace.md](references/workspace.md)
- [references/findings-schema.md](references/findings-schema.md)
- [references/code-review-loop.md](references/code-review-loop.md)
- [references/delivery.md](references/delivery.md)

Walkthrough: [docs/WORKFLOW.md](../../../docs/WORKFLOW.md)
