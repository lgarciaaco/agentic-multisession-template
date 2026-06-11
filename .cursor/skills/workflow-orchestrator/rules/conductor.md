# Conductor rules

**Runner:** parent agent (bound session).  
**Skill:** [SKILL.md](../SKILL.md) — entry point; load this file for phase behavior.  
**State:** `sessions/<codename>/workflow.json`

## Purpose

Single-chat orchestrator for Problem → Plan → Code → Review → PR → CI → Delivery. Autonomous inner loops; **user gates only at brief and plan**.

## Phase state machine

| Phase | Load rules | Exit |
|-------|------------|------|
| `intake` | problem-analyst.md | `problem-brief.md` drafted |
| `brief_review` | problem-analyst.md | user `accept brief` |
| `plan_loop` | plan-author + plan-reviewer (Task) | synthesizer APPROVE |
| `plan_user_review` | conductor presents plan + **refused dispositions only** | user `accept plan` |
| `implementation` | session-orchestrator + developer section | slice ready → **auto** code review |
| `code_review_loop` | code-reviewer + code-fixer (parent) | synthesizer PASS |
| `pr_creation` | git-commit + pr-create skills (parent) | SUCCESS → ci_observe |
| `ci_observe` | CI poll + [ci-fixer.md](ci-fixer.md) (parent) | GREEN → delivery |
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

When calling Task, pass the `model` from the appropriate spec: plan-loop agents → read `**Model:**` from `agents/plan-author.md` or `agents/plan-reviewer.md`; code-review specialists → read `**Model:**` from `.cursor/skills/code-reviewer/SKILL.md §2 Specialists`. See [SKILL.md § Model assignments](../SKILL.md#model-assignments) for the full table.

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
  if PASS: phase → pr_creation; break
  if FAIL (BLOCKER): escalate user immediately
  if INCOMPLETE:
    parent: code-fixer.md — fix REQUIRED; disposition SUGGESTION/NIT
    iteration++; new review-* workspace; goto loop top

if iteration >= max: escalate with reviews/r-NNN paths
else: auto pr_creation → ci_observe → delivery report → completed
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

## PR creation (autonomous — no user)

After code review PASS:

1. Load `.cursor/skills/git-commit/SKILL.md` — commit worktree changes.
2. Load `.cursor/skills/pr-create/SKILL.md` — push + draft PR against `pr_target_branch`.
3. `python3 scripts/workflow-advance-pr-creation.py <codename> SUCCESS <pr_url>`
4. On push/gh failure: `RETRY` or `FAIL`; escalate at max iterations.

## CI observe (autonomous — no user)

After PR creation SUCCESS:

```text
loop while iteration < loops.ci_observe.max:
  # Step 1: check merge state (detects rebase-needed BEFORE CI status)
  gh pr view <number> --json mergeStateStatus
  if mergeStateStatus == "CONFLICTING": verdict = CONFLICT

  # Step 2: poll CI (only if mergeable)
  gh pr checks <number>
  if all pass: verdict = GREEN
  if any fail: verdict = TEST_FAILURE
  if pending/stale: wait or verdict = TIMEOUT

  # Step 3: act on verdict
  if GREEN: phase → delivery; break
  if CONFLICT: rebase onto pr_target_branch, force-push, re-poll
  if TEST_FAILURE: load ci-fixer.md, fix, commit, force-push, re-poll
  workflow-ci-observe-advance.py <codename> <verdict>
  iteration++

if iteration >= max: escalate
else: auto delivery report → completed
```

**Merge conflict detection:** `gh pr checks` only reports CI check results — it does NOT surface merge conflicts. The conductor MUST run `gh pr view <number> --json mergeStateStatus` first. A `CONFLICTING` state means the branch needs rebasing regardless of CI status.

Never ask user between code review PASS and delivery.

## Status updates (between gates)

One-line progress only:

- "Implementing t1…"
- "Code review iteration 2 — INCOMPLETE (4 REQUIRED), fixing…"
- "Code review PASS — committing and opening PR…"
- "CI observe iteration 1 — TEST_FAILURE, fixing…"
- "CI observe GREEN — writing delivery report"

Never ask user to relay messages or choose the next pipeline step.

## Escalation (max iterations)

Present stuck summary with phase, iteration, verdict, artifact paths. Suggested: `reopen plan`, narrow scope, or manual fix + resume.

## Subroutines

| Phase | Invoke |
|-------|--------|
| plan_loop | Task agents per `agents/plan-*.md` |
| code_review_loop | code-reviewer SKILL + [code-fixer.md](code-fixer.md) |
| pr_creation | `.cursor/skills/git-commit/SKILL.md` + `.cursor/skills/pr-create/SKILL.md` |
| ci_observe | CI poll + [ci-fixer.md](ci-fixer.md) |
| implementation | [session-orchestrator/SKILL.md](../../session-orchestrator/SKILL.md) |

## Writable (conductor)

- `sessions/<codename>/workflow.json`, `artifacts/**`, `reviews/**`
- `sessions/<codename>/worktrees/**` in implementation and code_review_loop (fixer)
- Hub mode: hub worktree paths per BOUNDARIES.md

## Delivery

After CI observe **GREEN**, auto-run:

```bash
python3 scripts/workflow-write-delivery-report.py <codename>
```

Present `artifacts/delivery-report.md` in one screen; `phase → completed`. Not a user gate.
