# Research rationale (summary)

Patterns adopted for workflow-orchestrator role specs. Full session research may exist under `sessions/<codename>/research/` when a hub session drove design; this file is the generic distillate for shipped skills.

## Adopt

- Markdown artifact chain: brief → plan → implement → review
- Per-phase checklists with synthesizer verdicts (not checklist-only)
- Task spawn for plan author and plan reviewer; parent implements
- Intent-style criteria mapping (brief SC-n → plan tasks)
- Shape Up constraints/no-gos in brief; risks in plan
- Definition of Ready checks on plan tasks
- Three human gates only; autonomous plan and code loops

## Reject

- Cross-session inbox for workflow handoff
- Task subagent for implementation
- Persona/menu analyst framing
- Repo-wide spec corpora (session-scoped `artifacts/` instead)
- BLOCKER severity on plan review (no code under review)

## Adapt

- BMAD elicitation → interactive analyst until open questions empty
- write-like-a-human → final tone pass on brief only
- Spec Kit task granularity → `action-plan.md` single file
- Hub test commands when `mode: hub` or `scripts/` in plan touch points

## Resolved design decisions (M2)

| Question | Resolution | Where |
|----------|------------|-------|
| Implementation discovery | New scope → `reopen plan`; nits → inline task note | conductor.md |
| Max loop iterations | Default 5 in `workflow.loops.*.max` | conductor.md |
| Plan gate feedback | `artifacts/plan-feedback.md` + re-enter plan_loop | conductor.md |
| Hub test rule | Fire when `session_mode == hub` OR `scripts/` in Files/areas | plan-reviewer.md |
| Workspace IDs | `wf-*` for plan; `review-*` for code-reviewer | conductor.md |
