# Session orchestrator retirement checklist

**Status:** draft — user gate required before any deletion

## Overlap with `/start-work`

| session-orchestrator step | sessions-orchestrator equivalent |
|----------------------------|----------------------------------|
| `repos-status.sh` bootstrap | Parent `/sessions-orchestrator` assumes hub ready |
| `resolve-session.sh` / bind | Parent session bind; children bound in child chats |
| `set-session-scope.sh` | Parent scope + per-child scope at bootstrap |
| `ensure-worktrees.sh` | Child `/workflow-orchestrator` accept plan |

## User gate questions (before delete)

1. Should `/start-work` load **sessions-orchestrator** for parent-only bind, or stay thin?
2. Are all session-orchestrator triggers documented elsewhere?
3. Confirm no automation still references `.cursor/skills/session-orchestrator/SKILL.md` alone.

## Non-deletion rule

Do **not** remove `.cursor/skills/session-orchestrator/` until user answers **yes** to retirement after smoke-testing `/sessions-orchestrator` + child `/workflow-orchestrator`.
