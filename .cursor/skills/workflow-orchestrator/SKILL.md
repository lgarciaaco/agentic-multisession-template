---
name: workflow-orchestrator
description: >-
  Single-session pipeline: Problem → Plan → Code → Review → PR → CI → Delivery
  with autonomous inner loops. User gates at brief and plan only. Use for /workflow-orchestrator,
  full feature pipeline, problem brief, action plan, or workflow status. Loads when
  user wants end-to-end delivery without cross-session handoff.
---

# Workflow orchestrator

One chat, one conductor. Linear pipeline with autonomous plan and code loops between user gates. **Inbox feedback** from monitoring sessions counts at gates when correlated; poll every 2 minutes while awaiting a gate.

## Target

1. `./scripts/resolve-session.sh` → bound session required
2. State: `sessions/<codename>/workflow.json`
3. Artifacts: `sessions/<codename>/artifacts/`
4. Hub or product per `session.json` `mode`

## Triggers

| Trigger | Action |
|---------|--------|
| `/workflow-orchestrator` | Start or resume pipeline |
| `/workflow-orchestrator status` | One-screen status from `workflow.json` |
| `accept brief` / `accept` | Gate 1 (phase `brief_review`) |
| `accept plan` | Gate 2 → `./scripts/workflow-accept-plan.sh <codename>` |
| Inbox at gate | `./scripts/workflow-pull-inbox-gate.py <codename> [--apply]` — correlated messages count as gate feedback |
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
| `brief_review` | problem-analyst.md | accept brief (chat or correlated inbox) |
| `plan_loop` | plan-author + plan-reviewer (Task) | — |
| `plan_user_review` | conductor presents plan + refused dispositions | accept plan (chat or correlated inbox) |
| `implementation` | session-orchestrator + conductor developer section | — |
| `code_review_loop` | code-reviewer + code-fixer (parent) | — |
| `pr_creation` | git-commit + pr-create skills (parent) | — |
| `ci_observe` | CI poll + ci-fixer (parent) | — |
| `delivery` | delivery template | — |
| `completed` | — | — |

## `/workflow-orchestrator status` (one screen)

Read `workflow.json` and artifact paths; print:

```markdown
## Workflow status — <codename>

- **Phase:** <phase>
- **Gate brief_accepted:** <bool>
- **Gate plan_user_accepted:** <bool>
- **Plan loop:** <iteration>/<max> last <verdict>
- **Code review loop:** <iteration>/<max> last <verdict>
- **PR creation:** <iteration>/<max> last <verdict>
- **CI observe:** <iteration>/<max> last <verdict>
- **Brief:** sessions/<codename>/<brief path> (present|missing)
- **Plan:** sessions/<codename>/<plan path> (present|missing)
- **Next command:** <suggested user or agent action>
- **Inbox gate poll:** every 2m while phase is `brief_review` or `plan_user_review`
```

Do not ask the user to relay messages between agents or sessions.

## Pipeline (overview)

```text
intake → brief_review → [accept brief | inbox at gate]
  → plan_loop → plan_user_review → [accept plan | inbox at gate]
  → implementation → [auto] code_review_loop
  → [auto] pr_creation → [auto] ci_observe → delivery → completed
```

At `brief_review` and `plan_user_review`, follow [rules/conductor.md](rules/conductor.md) **Gate-entry checklist**: immediate `workflow-pull-inbox-gate.py --apply`, then arm `/loop 120s` for recurring pull. `beforeSubmitPrompt` hook auto-pull is a safety net only. Program children dual-write gate blockers to parent inbox before presenting the gate.

Autonomous loops — conductor runs without user between gates.

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

After user says **accept plan** (or inbox pull applies `accept plan`):

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

Prints `code_review_loop`. Never ask the user to commit first or choose between review and PR.

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
   - **PASS** → `phase: pr_creation`; auto commit + draft PR
   - **INCOMPLETE** → parent loads [rules/code-fixer.md](rules/code-fixer.md): fix REQUIRED; disposition SUGGESTION/NIT; **re-run loop** (new `review-*` workspace) — no user
   - **FAIL** (BLOCKER) → escalate immediately
   - iteration ≥ max → escalate

6. `./scripts/sync-session.sh <codename>` after each iteration

**Status line:** `Code review iteration N — INCOMPLETE (R REQUIRED), fixing…` or `Code review PASS — entering PR creation`

Intent reviewer uses **active task** acceptance only (via enriched manifest). See [references/code-review-loop.md](references/code-review-loop.md).

### PR creation

**Precondition:** `phase: pr_creation` (auto after code review PASS). No user gate.

1. Load `.cursor/skills/git-commit/SKILL.md` — commit all worktree changes (conventional-commit).
2. Load `.cursor/skills/pr-create/SKILL.md` — push and open draft PR against `pr_target_branch`.
3. Record PR URL on active task in `session.json`.
4. Advance:

```bash
python3 scripts/workflow-advance-pr-creation.py <codename> SUCCESS <pr_url>
```

On failure (push rejected, gh error): retry or escalate.

```bash
python3 scripts/workflow-advance-pr-creation.py <codename> RETRY
python3 scripts/workflow-advance-pr-creation.py <codename> FAIL
```

SUCCESS → `phase: ci_observe`. 5-iteration cap before escalation.

### CI observe loop

**Precondition:** `phase: ci_observe` (auto after PR creation SUCCESS). No user gate.

Each iteration:

1. Check mergeability: `gh pr view <pr_number> --json mergeStateStatus` — if `CONFLICTING`, verdict is `CONFLICT` (skip CI poll).
2. Poll CI: `gh pr checks <pr_number>` — classify pass/fail/pending.
3. Classify combined result:
   - **GREEN** → advance to `delivery`
   - **CONFLICT** → rebase onto `pr_target_branch`, force-push, re-poll
   - **TEST_FAILURE** → parent loads [rules/ci-fixer.md](rules/ci-fixer.md): fix, commit, force-push, re-poll
   - **TIMEOUT** / **FAIL** → escalate

3. Advance:

```bash
python3 scripts/workflow-ci-observe-advance.py <codename> <verdict>
```

4. Loop capped at 5 iterations; escalate with CI log summary after max.
5. `./scripts/sync-session.sh <codename>` after each iteration.

**Status line:** `CI observe iteration N — CONFLICT, rebasing…` or `CI observe GREEN — writing delivery report`

### Delivery

**Precondition:** `phase: delivery` (auto after CI observe GREEN).

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
- [ ] Inbox gate loop stopped after leaving `brief_review` / `plan_user_review`

## Writable

`sessions/<codename>/workflow.json`, `artifacts/**`, `reviews/workspace/wf-*/`, `artifacts/plan-review/`, session metadata. Implementation: `sessions/<codename>/worktrees/**` only (self-hosted hub: worktree, not hub root).

## Model assignments

Hardcoded per role. When Cursor releases new model slugs, update the file listed in the **To update** column **and the Model slug cell in this table**.

| Role | Runner | Model slug | To update |
|------|--------|------------|-----------|
| Plan author | Task | `gpt-5.3-codex` | `agents/plan-author.md` |
| Plan reviewer | Task | `claude-4.6-sonnet-medium-thinking` | `agents/plan-reviewer.md` |
| Code review specialists | Task (parallel) | `claude-4.6-sonnet-medium-thinking` | `.cursor/skills/code-reviewer/SKILL.md` |
| Problem analyst | Parent (inline) | inherits parent | — |
| Plan synthesizer | Parent (inline) | inherits parent | — |
| Implementation developer | Parent (inline) | inherits parent | — |
| Code-fixer | Parent (inline) | inherits parent | — |
| Scope collector | Parent (inline) | inherits parent | — |

**Rationale:** Codex for plan-author because plan writing is a structured-output task (IDs, aliases, acceptance criteria) where format precision matters more than deep reasoning. Thinking model for plan-reviewer and code-review specialists because their job is adversarial — tracing implication chains, finding DoR gaps, spotting subtle security or intent violations that surface-reading misses. Parent-inherit for all inline roles to preserve context continuity.

## References

- [workflow-schema.md](references/workflow-schema.md)
- [workspace.md](references/workspace.md)
- [persistence.md](references/persistence.md)
- [findings-schema.md](references/findings-schema.md)
- [research-rationale.md](references/research-rationale.md)
- [code-review-loop.md](references/code-review-loop.md)
- [pr-creation.md](references/pr-creation.md)
- [ci-observe-loop.md](references/ci-observe-loop.md)
- [delivery.md](references/delivery.md)
