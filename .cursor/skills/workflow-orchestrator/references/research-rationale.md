# Research rationale (internal)

Agent-internal design notes for workflow-orchestrator. Not user-facing release documentation.

## Adopt

- Markdown artifact chain: brief → plan → implement → review
- Per-phase checklists with synthesizer verdicts (not checklist-only)
- Task spawn for plan author and plan reviewer; parent implements
- Intent-style criteria mapping (brief SC-n → plan tasks)
- Scope constraints and explicit out-of-scope in brief; risks in plan
- Definition of Ready checks on plan tasks
- Three human gates only; autonomous plan and code loops

## Reject

- Cross-session inbox for workflow handoff
- Task subagent for implementation
- Persona/menu analyst framing
- Repo-wide spec corpora (session-scoped `artifacts/` instead)
- BLOCKER severity on plan review (no code under review)
- Conductor inlining plan author or plan reviewer work

## Adapt

- Interactive analyst until open questions empty
- write-like-a-human → final tone pass on brief only
- Single-file action plan (`action-plan.md`)
- Hub test commands when `mode: hub` or `scripts/` in plan touch points

## Resolved design decisions

| Question | Resolution | Where |
|----------|------------|-------|
| Implementation discovery | New scope → `reopen plan`; nits → inline task note | conductor.md |
| Max loop iterations | Default 5 in `workflow.loops.*.max` | conductor.md |
| Plan gate feedback | `artifacts/plan-feedback.md` + re-enter plan_loop | conductor.md |
| Hub test rule | Fire when `session_mode == hub` OR `scripts/` in Files/areas | plan-reviewer.md |
| Workspace IDs | `wf-*` for plan; `review-*` for code-reviewer | conductor.md |
| Subagent isolation | Conductor spawns Task agents only; no inline plan/findings | conductor.md |
