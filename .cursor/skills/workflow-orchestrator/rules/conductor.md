# Conductor rules

**Runner:** parent agent (bound session).  
**Skill:** [SKILL.md](../SKILL.md) — entry point; load this file for phase behavior.  
**State:** `sessions/<codename>/workflow.json`

## Purpose

Single-chat orchestrator for Problem → Plan → Code → Review → Delivery. Autonomous inner loops; **user gates only at brief and plan**.

## Phase state machine

| Phase | Load rules | Exit |
|-------|------------|------|
| `intake` | problem-analyst.md | `problem-brief.md` drafted |
| `brief_review` | problem-analyst.md | user `accept brief` |
| `plan_loop` | plan-author + plan-reviewer (Task) | synthesizer APPROVE |
| `plan_user_review` | conductor presents plan + **refused dispositions only** | user `accept plan` |
| `implementation` | session-orchestrator + developer section | slice ready → **auto** code review |
| `code_review_loop` | code-reviewer + code-fixer (parent) | synthesizer PASS |
| `delivery` | delivery template | auto → `completed` |
| `completed` | — | optional end session |

## Phase guards

Refuse phase skip:

- `plan_loop` until `gates.brief_accepted`
- `implementation` until `gates.plan_user_accepted`
- `code_review_loop` until implementation slice marked ready (see below)
- Never spawn Task subagent for implementation or code-fixer — parent implements

On guard violation: state current phase, missing gate, and required user command.

## Human gates (two)

| Gate | Command | Effect |
|------|---------|--------|
| 1 | `accept brief` / `accept` | `gates.brief_accepted: true`; freeze brief |
| 2 | `accept plan` | `gates.plan_user_accepted: true`; sync tasks → session.json |

Delivery report is **inform only** — not a gate. Never ask the user to approve delivery, commit, or open a PR before the autonomous code review loop runs.

**Reopen:** `python3 scripts/workflow-reopen-brief.py <codename>` · `python3 scripts/workflow-reopen-plan.py <codename>`

## Autonomy (mandatory)

When `workflow.json` exists, the conductor runs the pipeline **without** pausing for:

- uncommitted worktree changes (include in review scope)
- "commit + PR when ready"
- "code review loop or commit?"
- relay between agents

After coding a task slice finishes → immediately:

```bash
python3 scripts/workflow-mark-implementation-ready.py <codename> <task-id>
```

Then enter the code review loop — no user prompt.

## Subagent isolation (mandatory)

| Forbidden (conductor) | Required instead |
|-----------------------|------------------|
| Write or rewrite `artifacts/action-plan.md` in `plan_loop` | **Task(plan-author)** |
| Write `findings/plan.json` or plan verdict inline | **Task(plan-reviewer)** |
| Write specialist `findings/*.json` in code review | **Task** per code-reviewer SKILL |
| Skip fixer after INCOMPLETE | Parent loads [code-fixer.md](code-fixer.md) and fixes before re-review |

## Plan loop (autonomous — no user)

See SKILL.md **Plan loop**. Summary:

```text
plan-author → plan-reviewer → synthesize
REVISE until APPROVE (disposition validation for SUGGESTION/NIT)
→ plan_user_review (refused dispositions only) → user accept plan
```

## Code loop (autonomous — no user)

Specialists via **code-reviewer** skill Task subagents. Fixer is parent agent. Reviewer is authoritative.

See SKILL.md **Code review loop** and [../../code-reviewer/SKILL.md](../../code-reviewer/SKILL.md).

```text
# Enter (after implementation slice — no user gate)
python3 scripts/workflow-mark-implementation-ready.py <codename> <task-id>

loop while iteration < loops.code_review.max:
  scope collector (changeset + working tree when workflow session)
  enrich scope → workflow-code-review-enrich-scope.py
  Task specialists (parallel) → findings/*.json
  synthesizer → report.md + reviews/r-NNN.json
  workflow-code-review-advance.py
  if PASS: phase → delivery; break
  if FAIL (BLOCKER): escalate user immediately
  if INCOMPLETE:
    parent: code-fixer.md — fix REQUIRED; disposition SUGGESTION/NIT
    iteration++; new review-* workspace; goto loop top

if iteration >= max: escalate with reviews/r-NNN paths
else: auto delivery report → completed
```

**Disposition:** Same model as plan loop — fixer accepts/refuses SUGGESTION/NIT; specialists validate; synthesizer **INCOMPLETE** while open SUGGESTION/NIT remain in findings. **PASS** only when findings clear (validated refusals in `artifacts/code-review-disposition.md` only).

## Plan user review (gate 2)

When phase is `plan_user_review` after synthesizer **APPROVE**:

1. Present Approach + task summary + **refused dispositions only**
2. End with **`accept plan`** or `plan-feedback.md` → re-enter `plan_loop`
3. Do not ask open-ended questions

## Developer (implementation phase)

Parent agent — not Task subagent.

1. Read frozen `problem-brief.md` and user-accepted `action-plan.md`.
2. Edit `sessions/<codename>/worktrees/**` only.
3. Mark task `in_progress` while coding.
4. When task slice meets plan acceptance for this PR → mark task `done` (or ready) and **immediately** run `workflow-mark-implementation-ready.py` — do **not** ask about commits or PRs.
5. `./scripts/sync-session.sh <codename>` after metadata edits.

**Discovery during implementation:** new scope → stop; ask user to `reopen plan` or `reopen brief`.

## Status updates (between gates)

One-line progress only:

- "Implementing t1…"
- "Code review iteration 2 — INCOMPLETE (4 REQUIRED), fixing…"
- "Code review PASS — writing delivery report"

Never ask user to relay messages or choose the next pipeline step.

## Autopilot phases (no user turn)

When `workflow.json` exists and phase is one of below, **continue in the same turn** until the next user gate or escalation. Do **not** end the message with a question or offer to pause.

| Phase | User gate? | Conductor continues |
|-------|------------|---------------------|
| `plan_loop` | no | plan-author → plan-reviewer → synthesize → branch |
| `implementation` | no | code in worktree until slice ready → mark-ready |
| `code_review_loop` | no | code-reviewer → fixer on INCOMPLETE → advance → delivery on PASS |
| `delivery` | no | `workflow-write-delivery-report.py` → present report |
| `brief_review` | **yes** | await `accept brief` |
| `plan_user_review` | **yes** | await `accept plan` |

Read chat context **Resume:** line (from `workflow_next_action`) — it is the required next step, not optional.

## Forbidden closings (autopilot phases)

Do not end autopilot turns with:

- "Want me to continue…?" / "Should I…?" / "Pause here?"
- "Or would you prefer…?" / "Let me know if…"
- Offering commit, PR, or code review as a user choice

**Required closing:** one status line only, e.g. `Code review iteration 1 — running specialists…` or `Code review PASS — writing delivery report`.

## Escalation (max iterations)

Present stuck summary with phase, iteration, verdict, artifact paths. Suggested: `reopen plan`, narrow scope, or manual fix + resume.

## Subroutines

| Phase | Invoke |
|-------|--------|
| plan_loop | Task agents per `agents/plan-*.md` |
| code_review_loop | code-reviewer SKILL + [code-fixer.md](code-fixer.md) |
| implementation | [session-orchestrator/SKILL.md](../../session-orchestrator/SKILL.md) |

## Writable (conductor)

- `sessions/<codename>/workflow.json`, `artifacts/**`, `reviews/**`
- `sessions/<codename>/worktrees/**` in implementation and code_review_loop (fixer)
- Hub mode: hub worktree paths per BOUNDARIES.md

## Delivery

After code review **PASS**, auto-run:

```bash
python3 scripts/workflow-write-delivery-report.py <codename>
```

Present `artifacts/delivery-report.md` in one screen; `phase → completed`. Not a user gate.
