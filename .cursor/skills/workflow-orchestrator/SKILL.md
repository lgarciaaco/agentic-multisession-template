---
name: workflow-orchestrator
description: >-
  Single-session pipeline: Problem → Plan → Code → Review with autonomous inner
  loops. User gates at brief and plan only. Use for /workflow, full feature pipeline,
  problem brief, action plan, or workflow status. Loads when user wants end-to-end
  delivery without cross-session handoff.
---

# Workflow orchestrator

One chat, one conductor. Linear pipeline with autonomous plan and code loops between user gates.

## Target

1. `./scripts/resolve-session.sh` → bound session required
2. State: `sessions/<codename>/workflow.json`
3. Artifacts: `sessions/<codename>/artifacts/`
4. Hub or product per `session.json` `mode`

## Triggers

| Trigger | Action |
|---------|--------|
| `/workflow` | Start or resume pipeline |
| `/workflow status` | One-screen status from `workflow.json` |
| `accept brief` / `accept` | Gate 1 (phase `brief_review`) |
| `accept plan` | Gate 2 → `./scripts/workflow-accept-plan.sh <codename>` |
| `reopen brief` | `python3 scripts/workflow-reopen-brief.py <codename>` |
| `reopen plan` | `python3 scripts/workflow-reopen-plan.py <codename>` |

## Start or resume

1. `./scripts/resolve-session.sh` — must print codename
2. Bootstrap when starting fresh (skip files that already exist):
   - `mkdir -p sessions/<codename>/artifacts`
   - If no `workflow.json`: copy `sessions/_template/workflow.json`, ensure `phase: intake`
   - For each `sessions/_template/artifacts/*.md`: copy to `sessions/<codename>/artifacts/` if missing
3. If `workflow.json` present: read `phase` and **Resume** line from chat context (or `workflow_next_action` in `scripts/lib/workflow_resume.py`) — continue that phase; do not restart from chat history
4. Load [rules/conductor.md](rules/conductor.md) for current phase
5. `./scripts/sync-session.sh <codename>` after `workflow.json` or artifact bootstrap

## Phases

| Phase | Role rules | User gate |
|-------|------------|-----------|
| `intake` | [problem-analyst.md](rules/problem-analyst.md) | — |
| `brief_review` | problem-analyst.md | accept brief |
| `plan_loop` | plan-author + plan-reviewer (Task) | — |
| `plan_user_review` | conductor presents plan + refused dispositions | accept plan |
| `implementation` | session-orchestrator + conductor developer section | — |
| `code_review_loop` | code-reviewer + code-fixer (parent) | — |
| `delivery` | delivery template | — |
| `completed` | — | — |

## `/workflow status` (one screen)

Read `workflow.json` and artifact paths; print:

```markdown
## Workflow status — <codename>

- **Phase:** <phase>
- **Gate brief_accepted:** <bool>
- **Gate plan_user_accepted:** <bool>
- **Plan loop:** <iteration>/<max> last <verdict>
- **Code review loop:** <iteration>/<max> last <verdict>
- **Brief:** sessions/<codename>/<brief path> (present|missing)
- **Plan:** sessions/<codename>/<plan path> (present|missing)
- **Next command:** <suggested user or agent action>
```

Do not ask the user to relay messages between agents or sessions.

## Pipeline (overview)

```text
intake → brief_review → [accept brief]
  → plan_loop → plan_user_review → [accept plan]
  → implementation → [auto] code_review_loop → delivery → completed
```

Autonomous loops — conductor runs without user between gates.

**Autopilot rule:** After `accept plan`, through delivery, the conductor does not ask permission to continue. When `workflow-mark-implementation-ready.py` prints `code_review_loop`, **same turn** → load code-reviewer SKILL and run the loop. User gates: **brief** and **plan** only.

### Plan loop

**Precondition:** `gates.brief_accepted` true; phase `plan_loop`.

```bash
WORKFLOW_ID="wf-$(date -u +%Y%m%d-%H%M%S)"
WORKSPACE="sessions/<codename>/reviews/workspace/${WORKFLOW_ID}"
mkdir -p "${WORKSPACE}/findings"
```

Each iteration:

1. **Manifest** — write `plan_scope_manifest.json` (see [references/workspace.md](references/workspace.md)). On REVISE, set `prior_findings: findings/plan.json` and pass prior workspace findings to plan-author via manifest paths.
**Subagent isolation:** The conductor must spawn separate Task subagents for plan-author and plan-reviewer. Never write `action-plan.md` or `findings/plan.json` inline. See [rules/conductor.md](rules/conductor.md) **Subagent isolation**.

2. **Task(plan-author)** — [agents/plan-author.md](agents/plan-author.md); updates `artifacts/action-plan.md`.
3. **Task(plan-reviewer)** — [agents/plan-reviewer.md](agents/plan-reviewer.md); writes `${WORKSPACE}/findings/plan.json`.
4. **Synthesize** — conductor inline per [rules/agents/plan-synthesizer.md](rules/agents/plan-synthesizer.md), or:

```bash
python3 scripts/workflow-plan-synthesize.py <codename> sessions/<codename>/reviews/workspace/${WORKFLOW_ID}
```

5. **Branch** (read `workflow.json` after synthesize):
   - `APPROVE` → `phase: plan_user_review`; present plan to user (reviewer validated dispositions; open SUGGESTION/NIT must be absent from findings)
   - `REVISE` → increment iteration; new `${WORKFLOW_ID}-iter<n>` workspace if needed; goto step 1
     - Includes open SUGGESTION/NIT, REQUIRED gaps, invalid **refused** rationale, **accepted** not applied in plan
   - `REJECT` → escalate; suggest `reopen brief`
   - iteration ≥ `loops.plan.max` → escalate with `pr-NNN-report.md` paths

6. `./scripts/sync-session.sh <codename>` after each iteration

**Status line (no question):** `Plan review iteration N — REVISE (R REQUIRED)` or `Plan review APPROVE — awaiting your accept plan`

### Accept plan (gate 2)

After synthesizer **APPROVE**, conductor presents **Approach**, task summary, and **refused dispositions only** (validated deferrals from **Reviewer disposition**). Accepted items are already in the plan. See [rules/conductor.md](rules/conductor.md) **Plan user review**.

After user says **accept plan**:

```bash
./scripts/workflow-accept-plan.sh <codename>
```

Syncs `action-plan.md` tasks → `session.json` + `TASKS.md`, sets `plan_user_accepted`, `phase: implementation`, runs `ensure-worktrees.sh`. Path guards block worktree edits until this runs.

### Implementation phase

Load [session-orchestrator/SKILL.md](../session-orchestrator/SKILL.md) + [rules/conductor.md](rules/conductor.md) developer section. Edit worktrees only after accept plan.

### Code review loop

**Precondition:** implementation slice ready; phase `implementation` or `code_review_loop`. Does **not** require every plan task to be `done` (sequential PR tasks).

**Enter (no user gate)** — when coding for task `<task-id>` is complete:

```bash
python3 scripts/workflow-mark-implementation-ready.py <codename> <task-id>
```

Prints `code_review_loop`. Never ask the user to commit first or choose between review and PR. **Do not stop for user confirmation** — proceed immediately to step 1 below in the same turn.

Each iteration:

1. **Code reviewer** — load `.cursor/skills/code-reviewer/SKILL.md`; scope `changeset` **including uncommitted worktree changes** when `workflow.json` exists. After scope collector writes `scope_manifest.json`:

```bash
python3 scripts/workflow-code-review-enrich-scope.py <codename> sessions/<codename>/reviews/workspace/<review-id>
```

2. **Task specialists** (parallel) per code-reviewer SKILL; read `artifacts/code-review-disposition.md` on validation passes ([disposition-validation.md](../code-reviewer/rules/disposition-validation.md)).

3. **Synthesizer** (conductor inline) — merge findings; verdict via `synthesize_code_review_verdict()` in `scripts/lib/workflow_code_review.py`:
   - **FAIL** — any BLOCKER
   - **INCOMPLETE** — any REQUIRED; any open SUGGESTION/NIT (fixer must disposition; reviewer re-validates)
   - **PASS** — clean findings (validated refusals only in disposition file)

   Persist `reviews/r-NNN.json` + `report.md`.

4. **Advance:**

```bash
python3 scripts/workflow-code-review-advance.py <codename> [r-NNN]
```

5. **Branch:**
   - **PASS** → `phase: delivery`; auto-write delivery report
   - **INCOMPLETE** → parent loads [rules/code-fixer.md](rules/code-fixer.md): fix REQUIRED; disposition SUGGESTION/NIT; **re-run loop** (new `review-*` workspace) — no user
   - **FAIL** (BLOCKER) → escalate immediately
   - iteration ≥ max → escalate

6. `./scripts/sync-session.sh <codename>` after each iteration

**Status line:** `Code review iteration N — INCOMPLETE (R REQUIRED), fixing…` or `Code review PASS — writing delivery report`

Intent reviewer uses **active task** acceptance only (via enriched manifest). See [references/code-review-loop.md](references/code-review-loop.md).

### Delivery

**Precondition:** `phase: delivery` (auto after code review PASS).

```bash
python3 scripts/workflow-write-delivery-report.py <codename>
```

Sets `phase: completed`. Present report — **inform only**, not a user gate.

### Reopen gates

```bash
python3 scripts/workflow-reopen-brief.py <codename>   # gates → intake; clears brief + plan gates
python3 scripts/workflow-reopen-plan.py <codename>    # phase → plan_loop; clears plan gate only
```

Both print new `phase` and resume hint. Requires `workflow.json`.

## Artifacts

Templates: `sessions/_template/artifacts/`. Schema: [references/workflow-schema.md](references/workflow-schema.md).

| File | Writer |
|------|--------|
| `artifacts/problem-brief.md` | Analyst (parent) |
| `artifacts/action-plan.md` | Plan author (Task) |
| `artifacts/plan-feedback.md` | User at plan gate |
| `artifacts/delivery-report.md` | Conductor |
| `artifacts/plan-review/pr-NNN.*` | Plan synthesizer |

## Rule index

| Role | Rules | Task agent |
|------|-------|------------|
| Analyst | [problem-analyst.md](rules/problem-analyst.md) | parent |
| Plan author | [plan-author.md](rules/plan-author.md) | [agents/plan-author.md](agents/plan-author.md) |
| Plan reviewer | [plan-reviewer.md](rules/plan-reviewer.md) | [agents/plan-reviewer.md](agents/plan-reviewer.md) |
| Conductor | [conductor.md](rules/conductor.md) | inline |
| Code review | `.cursor/skills/code-reviewer/SKILL.md` | subroutine |

## Pre-delivery (conductor)

- [ ] `workflow.json` phase matches work done
- [ ] Gates not skipped
- [ ] `./scripts/sync-session.sh <codename>` after metadata or workflow edits
- [ ] No `session-inbox.sh` for workflow handoff

## Writable

`sessions/<codename>/workflow.json`, `artifacts/**`, `reviews/workspace/wf-*/`, `reviews/workspace/review-*/`, `artifacts/plan-review/`, session metadata. Implementation: `sessions/<codename>/worktrees/**` only (self-hosted hub: worktree, not hub root).

## References

- [workflow-schema.md](references/workflow-schema.md)
- [workspace.md](references/workspace.md)
- [persistence.md](references/persistence.md)
- [findings-schema.md](references/findings-schema.md)
- [research-rationale.md](references/research-rationale.md)
- [code-review-loop.md](references/code-review-loop.md)
- [delivery.md](references/delivery.md)
