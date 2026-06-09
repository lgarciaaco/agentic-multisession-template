# Workflow orchestrator (in progress)

Single-session pipeline: Problem → Plan → Code → Review.

| Milestone | Status |
|-----------|--------|
| M2 Role specs | done |
| M3 Spine | done |
| M4 Plan loop | done |
| M5 Implementation wiring | done — workflow-accept-plan.sh, gates |
| M6 Code review loop | done — enrich-scope, advance scripts, intent action-plan |
| M7 Delivery + resume | done — delivery report, reopen CLIs, context resume hint |
| M8 Docs + hub review | done — AGENTS/SESSIONS, test trio, walkthrough |

## Rule index

| Role | Rules | Agent procedure |
|------|-------|-----------------|
| Analyst | [rules/problem-analyst.md](rules/problem-analyst.md) | parent agent (conductor) |
| Plan author | [rules/plan-author.md](rules/plan-author.md) | [rules/agents/plan-author.md](rules/agents/plan-author.md) |
| Plan reviewer | [rules/plan-reviewer.md](rules/plan-reviewer.md) | [rules/agents/plan-reviewer.md](rules/agents/plan-reviewer.md) |
| Conductor | [rules/conductor.md](rules/conductor.md) | inline |
| Plan synthesizer | — | [rules/agents/plan-synthesizer.md](rules/agents/plan-synthesizer.md) |

## References

- [references/findings-schema.md](references/findings-schema.md)
- [references/research-rationale.md](references/research-rationale.md)
