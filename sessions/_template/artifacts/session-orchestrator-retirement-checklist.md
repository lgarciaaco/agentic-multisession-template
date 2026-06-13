# Session start retirement checklist

**Status:** completed — old skill path removed (no stub)

## Overlap with `/start-work`

| session-start step | sessions-orchestrator equivalent |
|--------------------|----------------------------------|
| `repos-status.sh` bootstrap | Parent `/sessions-orchestrator` assumes hub ready |
| `resolve-session.sh` / bind | Parent session bind; children bound in child chats |
| `set-session-scope.sh` | Parent scope + per-child scope at bootstrap |
| `ensure-worktrees.sh` | Child `/workflow-orchestrator` accept plan |

## Retirement notes

1. `/start-work` loads **session-start** (single-session bind), not **sessions-orchestrator** (program parent).
2. Triggers `start work`, `/start-work`, and `new task` live in `.cursor/skills/session-start/SKILL.md` and `.cursor/commands/start-work.md`.
3. Automation and docs reference `.cursor/skills/session-start/SKILL.md`; the old skill directory was deleted with no redirect.

## Verification

Smoke-test `/sessions-orchestrator` + child `/workflow-orchestrator` after rename. Path gate: no references to the deleted skill directory under `.cursor/skills/`.
