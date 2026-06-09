# Conductor rules

**Runner:** parent agent (bound session).  
**Skill:** [SKILL.md](../SKILL.md) — entry point; load this file for phase behavior.  
**State:** `sessions/<codename>/workflow.json`

## Purpose

Single-chat orchestrator for Problem → Plan → Code → Review. Autonomous inner loops; user gates only at brief, plan, and delivery.

## Phase state machine

| Phase | Load rules | Exit |
|-------|------------|------|
| `intake` | problem-analyst.md | `problem-brief.md` drafted |
| `brief_review` | problem-analyst.md | user `accept brief` |
| `plan_loop` | plan-author + plan-reviewer (Task) | synthesizer APPROVE |
| `plan_user_review` | plan-author.md (if feedback) | user `accept plan` |
| `implementation` | session-orchestrator + developer section below | all plan tasks done |
| `code_review_loop` | code-reviewer skill | PASS or PASS_WITH_NITS |
| `delivery` | delivery template | `delivery-report.md` shown |
| `completed` | — | optional end session |

## Phase guards

Refuse phase skip:

- `plan_loop` until `gates.brief_accepted`
- `implementation` until `gates.plan_user_accepted`
- `code_review_loop` until implementation tasks complete
- Never spawn Task subagent for implementation — parent implements

On guard violation: state current phase, missing gate, and required user command.

## Human gates (three)

| Gate | Command | Effect |
|------|---------|--------|
| 1 | `accept brief` / `accept` | `gates.brief_accepted: true`; freeze brief |
| 2 | `accept plan` | `gates.plan_user_accepted: true`; sync tasks → session.json |
| 3 | delivery report | inform only |

**Reopen:** `workflow-reopen-brief.py` clears `brief_accepted` + `plan_user_accepted`, resets plan loop, `phase → intake`. `workflow-reopen-plan.py` clears `plan_user_accepted`, `phase → plan_loop` (brief gate must stay true).

## Plan loop (autonomous — no user)

See SKILL.md **Plan loop (M4)** for executable steps. Helpers: `scripts/lib/workflow_plan.py`, `scripts/workflow-plan-synthesize.py`. Layout: [references/workspace.md](../references/workspace.md).

```text
workspace = sessions/<codename>/reviews/workspace/wf-<timestamp>/
iteration = workflow.loops.plan.iteration

loop while iteration < workflow.loops.plan.max (default 5):
  write plan_scope_manifest.json
  spawn Task(plan-author)  → artifacts/action-plan.md
  spawn Task(plan-reviewer) → findings/plan.json
  python3 scripts/workflow-plan-synthesize.py <codename> <workspace-rel>
  if APPROVE: phase → plan_user_review; break
  if REJECT: escalate user — suggest reopen brief
  if REVISE: iteration++; pass findings to next plan-author spawn

if iteration >= max: escalate with pr-NNN-report paths
else: present plan to user
```

**User feedback at plan gate:** append to `artifacts/plan-feedback.md`; re-enter `plan_loop` (do not ask "should I send to reviewer?").

**Workspace IDs:** `wf-YYYYMMDD-HHMMSS` for plan; keep `review-*` for code-reviewer unchanged.

## Code loop (autonomous — no user)

See SKILL.md **Code review loop (M6)** for executable steps. Helpers: `scripts/lib/workflow_code_review.py`, `scripts/workflow-code-review-enrich-scope.py`, `scripts/workflow-code-review-advance.py`. Layout: [references/code-review-loop.md](../references/code-review-loop.md).

```text
when all session.json tasks done: phase → code_review_loop

loop while iteration < workflow.loops.code_review.max (default 5):
  run code-reviewer skill (scope: changeset)
  enrich scope_manifest with action-plan acceptance
  workflow-code-review-advance.py after synthesizer
  if PASS | PASS_WITH_NITS: phase → delivery; break
  if INCOMPLETE | FAIL: fix per report; re-run (new review-id workspace)
if iteration >= max: escalate with reviews/r-NNN paths
```

## Developer (implementation phase)

Parent agent — not Task subagent.

1. Read frozen `problem-brief.md` and user-accepted `action-plan.md` — not chat history.
2. Run `./scripts/set-session-scope.sh` if title/goal thin.
3. On **accept plan**: `./scripts/workflow-accept-plan.sh <codename>` (sync tasks, gates, worktrees).
4. `./scripts/ensure-worktrees.sh <codename>` also run by accept-plan script.
5. Edit only `sessions/<codename>/worktrees/**` (or hub paths when `mode: hub`).
6. Mark tasks `in_progress` → `done` in dependency order.
7. `./scripts/sync-session.sh <codename>` after metadata edits.

**Discovery during implementation:**

- New scope not in brief → stop; ask user to `reopen plan` or `reopen brief`
- Small gap / nit / typo in plan → fix inline; note in task `note` field
- Do not expand scope without gate

## Status updates (between gates)

One-line progress only — not questions:

- "Plan review iteration 2 — REVISE (3 REQUIRED)"
- "Implementing t3…"
- "Code review iteration 1 — INCOMPLETE, fixing…"

Never ask user to relay messages between agents or sessions.

## Escalation (max iterations)

Present stuck summary with:

- Phase, iteration count, last verdict
- Paths: `artifacts/plan-review/pr-NNN-report.md` or `reviews/r-NNN.json`
- Suggested user action: feedback, `reopen plan`, or narrow scope

## Subroutines

| Phase | Invoke |
|-------|--------|
| plan_loop | Task agents per `agents/plan-*.md` |
| code_review_loop | `.cursor/skills/code-reviewer/SKILL.md` unchanged |
| implementation | `.cursor/skills/session-orchestrator/SKILL.md` |

## Writable (conductor)

- `sessions/<codename>/workflow.json`
- `sessions/<codename>/artifacts/**`
- `sessions/<codename>/reviews/workspace/wf-*/`
- `sessions/<codename>/artifacts/plan-review/`
- `sessions/<codename>/session.json`, `TASKS.md`, `progress.json` (metadata)
- `sessions/<codename>/worktrees/**` in implementation only
- Hub mode: `scripts/`, `.cursor/`, docs per BOUNDARIES.md

Never use `session-inbox.sh` for workflow handoff.

## Delivery (M7)

After code review PASS, `phase: delivery`. Generate report:

```bash
python3 scripts/workflow-write-delivery-report.py <codename>
```

Present `artifacts/delivery-report.md` to user; `phase → completed`. Template: `sessions/_template/artifacts/delivery-report.md`. See [references/delivery.md](../references/delivery.md).
